"""Regras de prescrição eletrônica.

Checagens em tempo real (nível Tasy):
  * Alergia — cruza princípio ativo × alergias ativas do paciente (bloqueio se grave).
  * Dose máxima — compara com `ref.medicamento.dose_maxima_dia`.
  * Ajuste renal — sugere ajuste pela faixa de TFG do paciente (`ajuste_renal` JSONB:
    lista de {tfg_max, ajuste} avaliada da menor faixa para a maior).
  * Interação medicamentosa — base de pares (`ref.interacao`), checada entre os
    itens da MESMA prescrição e contra as prescrições ATIVAS do paciente.
    'contraindicada' bloqueia; 'grave'/'moderada' alertam; 'leve' informa.

Alertas de gravidade 'bloqueio' impedem a assinatura — a prescrição só pode ser
salva como rascunho até o prescritor resolver o problema. Ao assinar, o eMAR é
gerado automaticamente para frequências reconhecidas (ver domain/horarios).
"""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.horarios import gerar_horarios
from ..models.clinico import Alergia, Emar, ExameResultado, RefExame
from ..models.hd import Prescricao, PrescricaoItem, RefInteracao, RefMedicamento
from ..schemas.auth import CurrentUser
from ..schemas.hd import AlertaItem, ItemCreate, ItemOut, PrescricaoCreate, PrescricaoOut

_GRAVIDADE_ALERTA = {
    "contraindicada": "bloqueio",
    "grave": "alerta",
    "moderada": "alerta",
    "leve": "info",
}


async def _tfg_recente(session: AsyncSession, paciente_id: str) -> float | None:
    """Última TFG registrada (exame código 'TFG'), se houver."""
    ref = await session.scalar(select(RefExame).where(RefExame.codigo == "TFG"))
    if ref is None:
        return None
    resultado = await session.scalar(
        select(ExameResultado)
        .where(ExameResultado.paciente_id == paciente_id,
               ExameResultado.exame_id == ref.id,
               ExameResultado.valor.is_not(None))
        .order_by(ExameResultado.data_coleta.desc())
        .limit(1)
    )
    return float(resultado.valor) if resultado else None


async def _checar_item(
    session: AsyncSession,
    paciente_id: str,
    item: ItemCreate,
    alergias: list[Alergia],
    tfg: float | None,
) -> tuple[list[AlertaItem], bool]:
    """Roda as checagens de um item. Retorna (alertas, ajuste_renal_aplicado)."""
    alertas: list[AlertaItem] = []
    ajuste_aplicado = False

    if item.medicamento_id is None:
        return alertas, ajuste_aplicado

    med = await session.get(RefMedicamento, item.medicamento_id)
    if med is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "medicamento não catalogado")

    # 1) Alergia (match por substring do princípio ativo, case-insensitive)
    principio = med.principio_ativo.lower()
    for alergia in alergias:
        sub = alergia.substancia.lower()
        if sub in principio or principio in sub:
            grave = (alergia.gravidade or "").lower() == "grave"
            alertas.append(AlertaItem(
                tipo="alergia",
                gravidade="bloqueio" if grave else "alerta",
                mensagem=(
                    f"Paciente com alergia registrada a '{alergia.substancia}'"
                    f" ({alergia.gravidade or 'gravidade não informada'})"
                ),
            ))

    # 2) Dose máxima diária
    if med.dose_maxima_dia is not None and item.dose is not None:
        if float(item.dose) > float(med.dose_maxima_dia):
            alertas.append(AlertaItem(
                tipo="dose_maxima",
                gravidade="alerta",
                mensagem=(
                    f"Dose {item.dose} {item.unidade_dose or ''} excede a máxima diária"
                    f" de {med.dose_maxima_dia} {med.unidade_dose or ''}".strip()
                ),
            ))

    # 3) Ajuste renal por faixa de TFG
    if med.ajuste_renal and tfg is not None:
        faixas = sorted(
            (f for f in med.ajuste_renal if isinstance(f, dict) and "tfg_max" in f),
            key=lambda f: f["tfg_max"],
        )
        for faixa in faixas:
            if tfg <= float(faixa["tfg_max"]):
                alertas.append(AlertaItem(
                    tipo="ajuste_renal",
                    gravidade="alerta",
                    mensagem=(
                        f"TFG {tfg:.0f} mL/min: {faixa.get('ajuste', 'ajustar dose')}"
                    ),
                ))
                ajuste_aplicado = True
                break

    return alertas, ajuste_aplicado


def _match_principio(principio: str, termo: str) -> bool:
    """Match tolerante entre princípio ativo e termo da base de interações."""
    a, b = principio.lower().strip(), termo.lower().strip()
    return a in b or b in a


async def _principios_ativos_vigentes(
    session: AsyncSession, paciente_id: str
) -> list[str]:
    """Princípios ativos das prescrições ATIVAS (assinadas) do paciente."""
    rows = await session.execute(
        select(RefMedicamento.principio_ativo)
        .join(PrescricaoItem, PrescricaoItem.medicamento_id == RefMedicamento.id)
        .join(Prescricao, Prescricao.id == PrescricaoItem.prescricao_id)
        .where(Prescricao.paciente_id == paciente_id, Prescricao.status == "ativa")
    )
    return [r[0] for r in rows]


async def _checar_interacoes(
    session: AsyncSession,
    principios_novos: list[str | None],
    principios_atuais: list[str],
) -> dict[int, list[AlertaItem]]:
    """Cruza os itens novos entre si e contra o que o paciente já usa.

    Retorna alertas por índice do item novo. Cada par da base é testado nos
    dois sentidos (A×B e B×A).
    """
    pares = list(await session.scalars(select(RefInteracao)))
    alertas: dict[int, list[AlertaItem]] = {}

    def _registrar(idx: int, par: RefInteracao, outro: str, origem: str) -> None:
        alertas.setdefault(idx, []).append(AlertaItem(
            tipo="interacao",
            gravidade=_GRAVIDADE_ALERTA.get(par.gravidade, "alerta"),
            mensagem=(
                f"Interação {par.gravidade} com {outro} ({origem}): "
                f"{par.efeito or 'ver protocolo'}. "
                f"{par.recomendacao or ''}".strip()
            ),
        ))

    for i, principio in enumerate(principios_novos):
        if principio is None:
            continue
        for par in pares:
            lados = [(par.principio_a, par.principio_b),
                     (par.principio_b, par.principio_a)]
            for meu_lado, outro_lado in lados:
                if not _match_principio(principio, meu_lado):
                    continue
                # contra os demais itens da mesma prescrição
                for j, outro in enumerate(principios_novos):
                    if j != i and outro is not None \
                            and _match_principio(outro, outro_lado):
                        _registrar(i, par, outro, "nesta prescrição")
                # contra as prescrições ativas do paciente
                for outro in principios_atuais:
                    if _match_principio(outro, outro_lado):
                        _registrar(i, par, outro, "em uso")
    return alertas


async def criar(
    session: AsyncSession, paciente_id: str, body: PrescricaoCreate, user: CurrentUser
) -> PrescricaoOut:
    if body.tipo not in ("geral", "enfermagem_sae"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "use a rota de HD para prescrição de hemodiálise")

    alergias = list(await session.scalars(
        select(Alergia).where(Alergia.paciente_id == paciente_id,
                              Alergia.ativo.is_(True))
    ))
    tfg = await _tfg_recente(session, paciente_id)

    # Princípios ativos para a checagem de interações
    principios_novos: list[str | None] = []
    for item in body.itens:
        if item.medicamento_id is None:
            principios_novos.append(None)
            continue
        med = await session.get(RefMedicamento, item.medicamento_id)
        if med is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "medicamento não catalogado")
        principios_novos.append(med.principio_ativo)
    principios_atuais = await _principios_ativos_vigentes(session, paciente_id)
    interacoes = await _checar_interacoes(session, principios_novos, principios_atuais)

    presc = Prescricao(
        paciente_id=paciente_id,
        unidade_id=user.unidade_id,
        prescritor_id=user.profissional_id,
        tipo=body.tipo,
    )
    session.add(presc)
    await session.flush()

    itens_out: list[ItemOut] = []
    tem_bloqueio = False
    for ordem, item in enumerate(body.itens):
        alertas, ajuste = await _checar_item(session, paciente_id, item, alergias, tfg)
        alertas.extend(interacoes.get(ordem, []))
        tem_bloqueio = tem_bloqueio or any(a.gravidade == "bloqueio" for a in alertas)
        row = PrescricaoItem(
            prescricao_id=presc.id,
            medicamento_id=item.medicamento_id,
            descricao_livre=item.descricao_livre,
            dose=item.dose,
            unidade_dose=item.unidade_dose,
            via=item.via,
            frequencia=item.frequencia,
            duracao=item.duracao,
            ajuste_renal_aplicado=ajuste,
            alertas=[a.model_dump() for a in alertas],
            ordem=ordem,
        )
        session.add(row)
        await session.flush()
        itens_out.append(ItemOut(
            id=row.id, medicamento_id=row.medicamento_id,
            descricao_livre=row.descricao_livre,
            dose=float(row.dose) if row.dose is not None else None,
            unidade_dose=row.unidade_dose, via=row.via,
            frequencia=row.frequencia, duracao=row.duracao,
            ajuste_renal_aplicado=row.ajuste_renal_aplicado, alertas=alertas,
        ))

    # Assinar só é permitido sem alertas de bloqueio
    if body.assinar:
        if tem_bloqueio:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "prescrição contém alerta de bloqueio (ex.: alergia grave) — "
                "resolva antes de assinar",
            )
        presc.status = "ativa"
        presc.assinada_em = dt.datetime.now(dt.timezone.utc)

        # eMAR automático para frequências reconhecidas (24h a partir de agora)
        rows_itens = await session.scalars(
            select(PrescricaoItem).where(PrescricaoItem.prescricao_id == presc.id))
        for row in rows_itens:
            for horario in gerar_horarios(row.frequencia, presc.assinada_em):
                session.add(Emar(
                    prescricao_item_id=row.id, paciente_id=paciente_id,
                    horario_previsto=horario,
                ))

    await session.commit()
    return PrescricaoOut(
        id=presc.id, tipo=presc.tipo, status=presc.status,
        assinada_em=presc.assinada_em, itens=itens_out, bloqueada=tem_bloqueio,
    )


async def montar_receita(
    session: AsyncSession, prescricao_id: str
) -> tuple[bytes, str, Prescricao]:
    """Gera o PDF do receituário de uma prescrição ASSINADA.

    Tipo: 'controle_especial' se houver item controlado (Portaria 344/98),
    senão 'simples'. Retorna (pdf, tipo, prescricao).
    """
    from ..models.core import Paciente, Profissional, Unidade
    from . import pdf_service

    presc = await session.get(Prescricao, prescricao_id)
    if presc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "prescrição não encontrada")
    if presc.assinada_em is None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "assine a prescrição antes de emitir a receita")

    itens_rows = list(await session.scalars(
        select(PrescricaoItem).where(PrescricaoItem.prescricao_id == presc.id)
        .order_by(PrescricaoItem.ordem)))
    itens: list[dict] = []
    tem_controlado = False
    for row in itens_rows:
        med = (await session.get(RefMedicamento, row.medicamento_id)
               if row.medicamento_id else None)
        controlado = bool(med.controlado) if med else False
        tem_controlado = tem_controlado or controlado
        itens.append({
            "nome": med.principio_ativo if med else (row.descricao_livre or "—"),
            "apresentacao": med.apresentacao if med else None,
            "dose": float(row.dose) if row.dose is not None else None,
            "unidade_dose": row.unidade_dose,
            "via": row.via,
            "frequencia": row.frequencia,
            "duracao": row.duracao,
            "controlado": controlado,
        })

    tipo = "controle_especial" if tem_controlado else "simples"
    paciente = await session.get(Paciente, presc.paciente_id)
    medico = await session.get(Profissional, presc.prescritor_id)
    unidade = await session.get(Unidade, presc.unidade_id)
    pdf = pdf_service.gerar_pdf_receita(paciente, medico, unidade, itens, tipo,
                                        presc.assinada_em)
    return pdf, tipo, presc


async def listar(session: AsyncSession, paciente_id: str) -> list[PrescricaoOut]:
    prescricoes = await session.scalars(
        select(Prescricao)
        .where(Prescricao.paciente_id == paciente_id)
        .order_by(Prescricao.inicio.desc())
    )
    out: list[PrescricaoOut] = []
    for p in prescricoes:
        itens = await session.scalars(
            select(PrescricaoItem)
            .where(PrescricaoItem.prescricao_id == p.id)
            .order_by(PrescricaoItem.ordem)
        )
        itens_out = [
            ItemOut(
                id=i.id, medicamento_id=i.medicamento_id,
                descricao_livre=i.descricao_livre,
                dose=float(i.dose) if i.dose is not None else None,
                unidade_dose=i.unidade_dose, via=i.via,
                frequencia=i.frequencia, duracao=i.duracao,
                ajuste_renal_aplicado=i.ajuste_renal_aplicado,
                alertas=[AlertaItem(**a) for a in (i.alertas or [])],
            )
            for i in itens
        ]
        out.append(PrescricaoOut(
            id=p.id, tipo=p.tipo, status=p.status, assinada_em=p.assinada_em,
            itens=itens_out,
            bloqueada=any(a.gravidade == "bloqueio" for i in itens_out for a in i.alertas),
        ))
    return out

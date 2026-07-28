"""Regras de prescrição eletrônica.

Checagens em tempo real (nível Tasy):
  * Alergia — cruza princípio ativo × alergias ativas do paciente (bloqueio se grave).
  * Dose máxima — compara com `ref.medicamento.dose_maxima_dia`.
  * Ajuste renal — sugere ajuste pela faixa de TFG do paciente (`ajuste_renal` JSONB:
    lista de {tfg_max, ajuste} avaliada da menor faixa para a maior).
  * (Interação medicamentosa: estrutura pronta em `alertas`; base de pares na fase 2.)

Alertas de gravidade 'bloqueio' impedem a assinatura — a prescrição só pode ser
salva como rascunho até o prescritor resolver o problema.
"""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.clinico import Alergia, ExameResultado, RefExame
from ..models.hd import Prescricao, PrescricaoItem, RefMedicamento
from ..schemas.auth import CurrentUser
from ..schemas.hd import AlertaItem, ItemCreate, ItemOut, PrescricaoCreate, PrescricaoOut


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

    await session.commit()
    return PrescricaoOut(
        id=presc.id, tipo=presc.tipo, status=presc.status,
        assinada_em=presc.assinada_em, itens=itens_out, bloqueada=tem_bloqueio,
    )


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

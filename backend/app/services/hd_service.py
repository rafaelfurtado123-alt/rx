"""Regras de hemodiálise: prescrição de HD (nível Tasy) e ciclo da sessão.

Ciclo da sessão:
    recepção (peso pré, PA, FC, Tª, queixas — alerta de ganho interdialítico)
    → início → parâmetros em tempo real → intercorrências
    → encerramento (peso pós, UF real; Kt/V, URR e nPCR automáticos)
"""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain import calculos
from ..models.hd import (
    AcessoVascular,
    Intercorrencia,
    Prescricao,
    PrescricaoHD,
    SessaoHD,
    SessaoParametro,
)
from ..schemas.auth import CurrentUser
from ..schemas.hd import (
    AcessoCreate,
    AcessoOut,
    AlertaItem,
    EncerramentoRequest,
    IntercorrenciaRequest,
    ParametroRequest,
    PrescricaoHDCreate,
    PrescricaoHDOut,
    RecepcaoRequest,
    SessaoOut,
)

# Ganho interdialítico acima deste % do peso seco gera alerta na recepção.
GANHO_INTERDIALITICO_MAX_PCT = 5.0


# ------------------------- Acesso vascular -------------------------
async def criar_acesso(
    session: AsyncSession, paciente_id: str, body: AcessoCreate
) -> AcessoOut:
    acesso = AcessoVascular(paciente_id=paciente_id, tipo=body.tipo,
                            lado=body.lado, localizacao=body.localizacao)
    session.add(acesso)
    await session.commit()
    return AcessoOut(id=acesso.id, tipo=acesso.tipo, lado=acesso.lado,
                     localizacao=acesso.localizacao, status=acesso.status)


async def listar_acessos(session: AsyncSession, paciente_id: str) -> list[AcessoOut]:
    rows = await session.scalars(
        select(AcessoVascular).where(AcessoVascular.paciente_id == paciente_id)
    )
    return [AcessoOut(id=a.id, tipo=a.tipo, lado=a.lado,
                      localizacao=a.localizacao, status=a.status) for a in rows]


# ------------------------- Prescrição de HD -------------------------
def _validar_prescricao_hd(body: PrescricaoHDCreate) -> list[AlertaItem]:
    """Validações clínicas cruzadas da prescrição de HD."""
    alertas: list[AlertaItem] = []

    if body.peso_atual_kg and body.peso_seco_kg:
        volume = calculos.volume_uf(body.peso_atual_kg, body.peso_seco_kg)
        if body.uf_prescrita_l is not None and body.uf_prescrita_l < volume:
            alertas.append(AlertaItem(
                tipo="uf_insuficiente", gravidade="alerta",
                mensagem=(f"UF prescrita ({body.uf_prescrita_l} L) abaixo do excesso "
                          f"de peso ({volume} L)"),
            ))

    if (body.uf_prescrita_l is not None and body.uf_maxima_l is not None
            and body.uf_prescrita_l > body.uf_maxima_l):
        alertas.append(AlertaItem(
            tipo="uf_acima_maxima", gravidade="bloqueio",
            mensagem=(f"UF prescrita ({body.uf_prescrita_l} L) excede a UF máxima "
                      f"({body.uf_maxima_l} L)"),
        ))

    # Taxa de UF > 13 mL/kg/h associa-se a hipotensão/mortalidade — alerta clínico.
    if body.uf_prescrita_l and body.peso_seco_kg and body.duracao_min:
        taxa = (body.uf_prescrita_l * 1000) / body.peso_seco_kg / (body.duracao_min / 60)
        if taxa > 13:
            alertas.append(AlertaItem(
                tipo="taxa_uf_alta", gravidade="alerta",
                mensagem=f"Taxa de UF {taxa:.1f} mL/kg/h acima de 13 mL/kg/h",
            ))

    return alertas


async def criar_prescricao_hd(
    session: AsyncSession, paciente_id: str, body: PrescricaoHDCreate, user: CurrentUser
) -> PrescricaoHDOut:
    alertas = _validar_prescricao_hd(body)
    tem_bloqueio = any(a.gravidade == "bloqueio" for a in alertas)
    if body.assinar and tem_bloqueio:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "prescrição de HD contém alerta de bloqueio — resolva antes de assinar",
        )

    if body.acesso_id is not None:
        acesso = await session.get(AcessoVascular, body.acesso_id)
        if acesso is None or str(acesso.paciente_id) != str(paciente_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND,
                                "acesso vascular não encontrado para o paciente")

    presc = Prescricao(
        paciente_id=paciente_id, unidade_id=user.unidade_id,
        prescritor_id=user.profissional_id, tipo="hd",
        status="ativa" if body.assinar else "rascunho",
        assinada_em=dt.datetime.now(dt.timezone.utc) if body.assinar else None,
    )
    session.add(presc)
    await session.flush()

    hd = PrescricaoHD(
        prescricao_id=presc.id,
        modalidade=body.modalidade,
        duracao_min=body.duracao_min,
        qb_ml_min=body.qb_ml_min,
        qd_ml_min=body.qd_ml_min,
        dialisador_modelo=body.dialisador_modelo,
        dialisador_reuso=body.dialisador_reuso,
        acesso_id=body.acesso_id,
        ponto_puncao=body.ponto_puncao,
        peso_atual_kg=body.peso_atual_kg,
        peso_seco_kg=body.peso_seco_kg,
        uf_prescrita_l=body.uf_prescrita_l,
        uf_maxima_l=body.uf_maxima_l,
        perfil_sodio=body.perfil_sodio,
        perfil_bicarbonato=body.perfil_bicarbonato,
        condutividade=body.condutividade,
        temperatura_banho=body.temperatura_banho,
        heparinizacao=body.heparinizacao,
        solucoes_json=body.solucoes,
    )
    session.add(hd)
    await session.commit()
    await session.refresh(hd)  # carrega volume_calculado_l gerado pelo banco

    return _hd_out(hd, presc, alertas)


async def listar_prescricoes_hd(
    session: AsyncSession, paciente_id: str
) -> list[PrescricaoHDOut]:
    rows = await session.execute(
        select(PrescricaoHD, Prescricao)
        .join(Prescricao, Prescricao.id == PrescricaoHD.prescricao_id)
        .where(Prescricao.paciente_id == paciente_id)
        .order_by(Prescricao.inicio.desc())
    )
    return [_hd_out(hd, presc, []) for hd, presc in rows]


def _hd_out(hd: PrescricaoHD, presc: Prescricao,
            alertas: list[AlertaItem]) -> PrescricaoHDOut:
    def _f(v):
        return float(v) if v is not None else None

    return PrescricaoHDOut(
        id=hd.id, prescricao_id=presc.id, modalidade=hd.modalidade,
        duracao_min=hd.duracao_min, qb_ml_min=hd.qb_ml_min, qd_ml_min=hd.qd_ml_min,
        dialisador_modelo=hd.dialisador_modelo, acesso_id=hd.acesso_id,
        ponto_puncao=hd.ponto_puncao,
        peso_atual_kg=_f(hd.peso_atual_kg), peso_seco_kg=_f(hd.peso_seco_kg),
        uf_prescrita_l=_f(hd.uf_prescrita_l), uf_maxima_l=_f(hd.uf_maxima_l),
        volume_calculado_l=_f(hd.volume_calculado_l),
        perfil_sodio=hd.perfil_sodio, perfil_bicarbonato=hd.perfil_bicarbonato,
        heparinizacao=hd.heparinizacao,
        solucoes=hd.solucoes_json if isinstance(hd.solucoes_json, list) else None,
        status=presc.status, assinada_em=presc.assinada_em, alertas=alertas,
    )


# ------------------------- Sessão de HD -------------------------
async def recepcao(
    session: AsyncSession, paciente_id: str, body: RecepcaoRequest, user: CurrentUser
) -> SessaoOut:
    """Cria a sessão na recepção do paciente (pré-diálise)."""
    alertas: list[AlertaItem] = []
    peso_seco: float | None = None

    if body.prescricao_hd_id is not None:
        hd = await session.get(PrescricaoHD, body.prescricao_hd_id)
        if hd is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND,
                                "prescrição de HD não encontrada")
        peso_seco = float(hd.peso_seco_kg) if hd.peso_seco_kg is not None else None

    # Alerta de ganho interdialítico excessivo (> 5% do peso seco)
    if peso_seco:
        ganho = body.peso_pre_kg - peso_seco
        pct = ganho / peso_seco * 100
        if pct > GANHO_INTERDIALITICO_MAX_PCT:
            alertas.append(AlertaItem(
                tipo="ganho_interdialitico", gravidade="alerta",
                mensagem=(f"Ganho interdialítico de {ganho:.1f} kg "
                          f"({pct:.1f}% do peso seco)"),
            ))

    sessao = SessaoHD(
        paciente_id=paciente_id, unidade_id=user.unidade_id,
        prescricao_hd_id=body.prescricao_hd_id,
        peso_pre_kg=body.peso_pre_kg, pa_pre=body.pa_pre, fc_pre=body.fc_pre,
        temp_pre=body.temp_pre, queixas=body.queixas,
    )
    session.add(sessao)
    await session.commit()
    return _sessao_out(sessao, alertas)


async def iniciar(
    session: AsyncSession, sessao_id: str, maquina: str | None, user: CurrentUser
) -> SessaoOut:
    sessao = await _get_sessao(session, sessao_id)
    if sessao.inicio is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "sessão já iniciada")
    sessao.inicio = dt.datetime.now(dt.timezone.utc)
    sessao.maquina = maquina
    if user.papel == "tecnico":
        sessao.tecnico_id = user.profissional_id
    elif user.papel == "enfermeiro":
        sessao.enfermeiro_id = user.profissional_id
    await session.commit()
    return _sessao_out(sessao, [])


async def registrar_parametro(
    session: AsyncSession, sessao_id: str, body: ParametroRequest
) -> dict:
    sessao = await _get_sessao(session, sessao_id)
    if sessao.inicio is None or sessao.fim is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "sessão não está em andamento")
    row = SessaoParametro(
        sessao_id=sessao.id, pa=body.pa, fc=body.fc, qb_ml_min=body.qb_ml_min,
        ptm=body.ptm, fluxo_uf=body.fluxo_uf, condutividade=body.condutividade,
        temperatura=body.temperatura,
    )
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "ok": True}


async def registrar_intercorrencia(
    session: AsyncSession, sessao_id: str, body: IntercorrenciaRequest,
    user: CurrentUser,
) -> dict:
    sessao = await _get_sessao(session, sessao_id)
    row = Intercorrencia(
        sessao_id=sessao.id, tipo=body.tipo, descricao=body.descricao,
        conduta=body.conduta, responsavel_id=user.profissional_id,
    )
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "ok": True}


async def encerrar(
    session: AsyncSession, sessao_id: str, body: EncerramentoRequest
) -> SessaoOut:
    """Encerra a sessão e calcula Kt/V, URR e nPCR quando as ureias existem."""
    sessao = await _get_sessao(session, sessao_id)
    if sessao.inicio is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "sessão não foi iniciada")
    if sessao.fim is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "sessão já encerrada")

    sessao.fim = dt.datetime.now(dt.timezone.utc)
    sessao.peso_pos_kg = body.peso_pos_kg
    sessao.pa_pos = body.pa_pos
    sessao.fc_pos = body.fc_pos

    # UF real: informada ou derivada da balança (peso pré − peso pós)
    if body.uf_real_l is not None:
        sessao.uf_real_l = body.uf_real_l
    elif sessao.peso_pre_kg is not None:
        sessao.uf_real_l = calculos.volume_uf(float(sessao.peso_pre_kg),
                                              body.peso_pos_kg)

    # Adequação automática (Daugirdas) se as ureias foram informadas
    if body.ureia_pre and body.ureia_pos:
        duracao_h = (sessao.fim - sessao.inicio).total_seconds() / 3600
        # Duração real irrisória (testes/sessão relâmpago): usa a prescrita se houver
        if duracao_h < 0.5 and sessao.prescricao_hd_id:
            hd = await session.get(PrescricaoHD, sessao.prescricao_hd_id)
            if hd is not None:
                duracao_h = hd.duracao_min / 60
        adequacao = calculos.adequacao(
            body.ureia_pre, body.ureia_pos, duracao_h,
            float(sessao.uf_real_l or 0), body.peso_pos_kg,
        )
        sessao.ktv = adequacao.ktv
        sessao.urr = adequacao.urr
        sessao.npcr = adequacao.npcr

    alertas: list[AlertaItem] = []
    if sessao.ktv is not None and float(sessao.ktv) < 1.2:
        alertas.append(AlertaItem(
            tipo="ktv_baixo", gravidade="alerta",
            mensagem=f"Kt/V {sessao.ktv} abaixo da meta 1.2 (3x/semana)",
        ))

    await session.commit()
    return _sessao_out(sessao, alertas)


async def listar_sessoes(session: AsyncSession, paciente_id: str) -> list[SessaoOut]:
    rows = await session.scalars(
        select(SessaoHD).where(SessaoHD.paciente_id == paciente_id)
        .order_by(SessaoHD.id.desc())
    )
    return [_sessao_out(s, []) for s in rows]


async def _get_sessao(session: AsyncSession, sessao_id: str) -> SessaoHD:
    sessao = await session.get(SessaoHD, sessao_id)
    if sessao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "sessão não encontrada")
    return sessao


def _sessao_out(s: SessaoHD, alertas: list[AlertaItem]) -> SessaoOut:
    def _f(v):
        return float(v) if v is not None else None

    return SessaoOut(
        id=s.id, paciente_id=s.paciente_id, prescricao_hd_id=s.prescricao_hd_id,
        peso_pre_kg=_f(s.peso_pre_kg), pa_pre=s.pa_pre, fc_pre=s.fc_pre,
        temp_pre=_f(s.temp_pre), queixas=s.queixas,
        inicio=s.inicio, fim=s.fim, maquina=s.maquina,
        peso_pos_kg=_f(s.peso_pos_kg), uf_real_l=_f(s.uf_real_l),
        pa_pos=s.pa_pos, fc_pos=s.fc_pos,
        ktv=_f(s.ktv), urr=_f(s.urr), npcr=_f(s.npcr),
        alertas=alertas,
    )

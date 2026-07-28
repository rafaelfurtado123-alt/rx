"""Ambulatório conservador: agenda de consultas nefrológicas + painel.

O paciente em tratamento conservador (DRC sem TRS) é acompanhado por consultas
agendadas. Marcar uma consulta como 'realizada' cria o episódio clínico
correspondente na timeline do prontuário. O painel resume a população
conservadora e destaca os estágios 4–5 (candidatos a preparo para TRS —
confecção de acesso, vacinação, educação do paciente).
"""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.clinico import ConsultaAgendada, Episodio
from ..models.core import Paciente
from ..schemas.ambulatorio import (
    ConsultaCreate,
    ConsultaOut,
    ConsultaStatusRequest,
    PainelAmbulatorio,
)
from ..schemas.auth import CurrentUser

TIPOS = ("primeira_consulta", "retorno", "preparo_trs")
STATUS_FINAIS = ("realizada", "faltou", "cancelada")


async def agendar(
    session: AsyncSession, paciente_id: str, body: ConsultaCreate, user: CurrentUser
) -> ConsultaOut:
    if body.tipo not in TIPOS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "tipo de consulta inválido")
    paciente = await session.get(Paciente, paciente_id)
    if paciente is None or paciente.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "paciente não encontrado")

    consulta = ConsultaAgendada(
        paciente_id=paciente_id, unidade_id=user.unidade_id,
        profissional_id=body.profissional_id or user.profissional_id,
        data_hora=body.data_hora, tipo=body.tipo, observacao=body.observacao,
    )
    session.add(consulta)
    await session.commit()
    return await _to_out(session, consulta)


async def agenda_do_dia(
    session: AsyncSession, unidade_id: str, data: dt.date
) -> list[ConsultaOut]:
    ini = dt.datetime.combine(data, dt.time.min, tzinfo=dt.timezone.utc)
    fim = ini + dt.timedelta(days=1)
    rows = await session.scalars(
        select(ConsultaAgendada)
        .where(ConsultaAgendada.unidade_id == unidade_id,
               ConsultaAgendada.data_hora >= ini,
               ConsultaAgendada.data_hora < fim)
        .order_by(ConsultaAgendada.data_hora)
    )
    return [await _to_out(session, c) for c in rows]


async def atualizar_status(
    session: AsyncSession, consulta_id: str, body: ConsultaStatusRequest,
    user: CurrentUser,
) -> ConsultaOut:
    """Fecha a consulta; 'realizada' cria o episódio clínico na timeline."""
    if body.status not in STATUS_FINAIS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "status inválido")
    consulta = await session.get(ConsultaAgendada, consulta_id)
    if consulta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "consulta não encontrada")
    if consulta.status in STATUS_FINAIS:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"consulta já fechada como '{consulta.status}'")

    consulta.status = body.status
    if body.observacao:
        consulta.observacao = body.observacao

    if body.status == "realizada":
        episodio = Episodio(
            paciente_id=consulta.paciente_id, unidade_id=consulta.unidade_id,
            tipo="consulta", inicio=dt.datetime.now(dt.timezone.utc),
            responsavel_id=user.profissional_id,
            resumo=f"Consulta ambulatorial ({consulta.tipo})",
        )
        session.add(episodio)
        await session.flush()
        consulta.episodio_id = episodio.id

    await session.commit()
    return await _to_out(session, consulta)


async def painel(session: AsyncSession, unidade_id: str) -> PainelAmbulatorio:
    from ..models.core import PacienteUnidade

    conservadores = list(await session.scalars(
        select(Paciente)
        .join(PacienteUnidade, PacienteUnidade.paciente_id == Paciente.id)
        .where(PacienteUnidade.unidade_id == unidade_id,
               PacienteUnidade.ativo.is_(True),
               Paciente.deleted_at.is_(None),
               Paciente.segmento == "conservador")
    ))
    por_estagio: dict[str, int] = {}
    candidatos = 0
    for p in conservadores:
        chave = f"estagio_{p.estagio_drc}" if p.estagio_drc else "sem_estadiamento"
        por_estagio[chave] = por_estagio.get(chave, 0) + 1
        if p.estagio_drc in (4, 5):
            candidatos += 1

    hoje = dt.datetime.now(dt.timezone.utc).date()
    ini_hoje = dt.datetime.combine(hoje, dt.time.min, tzinfo=dt.timezone.utc)

    consultas_hoje = await session.scalar(
        select(func.count()).select_from(ConsultaAgendada)
        .where(ConsultaAgendada.unidade_id == unidade_id,
               ConsultaAgendada.data_hora >= ini_hoje,
               ConsultaAgendada.data_hora < ini_hoje + dt.timedelta(days=1))
    ) or 0
    consultas_semana = await session.scalar(
        select(func.count()).select_from(ConsultaAgendada)
        .where(ConsultaAgendada.unidade_id == unidade_id,
               ConsultaAgendada.data_hora >= ini_hoje,
               ConsultaAgendada.data_hora < ini_hoje + dt.timedelta(days=7))
    ) or 0

    return PainelAmbulatorio(
        pacientes_conservador=len(conservadores), por_estagio=por_estagio,
        consultas_hoje=consultas_hoje, consultas_semana=consultas_semana,
        candidatos_preparo_trs=candidatos,
    )


async def _to_out(session: AsyncSession, c: ConsultaAgendada) -> ConsultaOut:
    paciente = await session.get(Paciente, c.paciente_id)
    return ConsultaOut(
        id=c.id, paciente_id=c.paciente_id,
        paciente_nome=paciente.nome if paciente else None,
        paciente_segmento=paciente.segmento if paciente else None,
        profissional_id=c.profissional_id, data_hora=c.data_hora,
        tipo=c.tipo, status=c.status, observacao=c.observacao,
        episodio_id=c.episodio_id,
    )

"""eMAR — checagem eletrônica de administração de medicamentos.

O eMAR é gerado automaticamente na assinatura da prescrição (frequências
reconhecidas) ou agendado manualmente. A administração registra executante,
horário real, lote e status; um registro fechado não pode ser reaberto.
"""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.clinico import Emar
from ..models.hd import PrescricaoItem, RefMedicamento
from ..schemas.auth import CurrentUser
from ..schemas.hd import EmarAgendarRequest, EmarOut, EmarRegistrarRequest

_STATUS_FINAIS = ("administrado", "recusado", "omitido")


async def agendar(
    session: AsyncSession, paciente_id: str, body: EmarAgendarRequest
) -> list[EmarOut]:
    """Agendamento manual de horários para um item de prescrição."""
    item = await session.get(PrescricaoItem, body.prescricao_item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "item de prescrição não encontrado")
    criados: list[Emar] = []
    for horario in body.horarios:
        row = Emar(prescricao_item_id=item.id, paciente_id=paciente_id,
                   horario_previsto=horario)
        session.add(row)
        criados.append(row)
    await session.commit()
    return [await _to_out(session, r) for r in criados]


async def listar(
    session: AsyncSession, paciente_id: str, pendentes: bool = False
) -> list[EmarOut]:
    stmt = select(Emar).where(Emar.paciente_id == paciente_id)
    if pendentes:
        stmt = stmt.where(Emar.status.in_(("previsto", "adiado")))
    stmt = stmt.order_by(Emar.horario_previsto)
    rows = await session.scalars(stmt)
    return [await _to_out(session, r) for r in rows]


async def registrar(
    session: AsyncSession, emar_id: str, body: EmarRegistrarRequest, user: CurrentUser
) -> EmarOut:
    """Registra a administração (ou recusa/omissão) de uma dose prevista."""
    if body.status not in ("administrado", "recusado", "omitido", "adiado"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "status inválido")

    row = await session.get(Emar, emar_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "registro eMAR não encontrado")
    if row.status in _STATUS_FINAIS:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"registro já fechado como '{row.status}'")

    row.status = body.status
    row.lote = body.lote
    row.observacao = body.observacao
    if body.status in _STATUS_FINAIS:
        row.horario_realizado = dt.datetime.now(dt.timezone.utc)
        row.executante_id = user.profissional_id
    await session.commit()
    return await _to_out(session, row)


async def _to_out(session: AsyncSession, row: Emar) -> EmarOut:
    item = await session.get(PrescricaoItem, row.prescricao_item_id)
    med = None
    if item is not None and item.medicamento_id is not None:
        med = await session.get(RefMedicamento, item.medicamento_id)
    return EmarOut(
        id=row.id, prescricao_item_id=row.prescricao_item_id,
        medicamento=med.principio_ativo if med else (
            item.descricao_livre if item else None),
        dose=float(item.dose) if item and item.dose is not None else None,
        unidade_dose=item.unidade_dose if item else None,
        via=item.via if item else None,
        horario_previsto=row.horario_previsto,
        horario_realizado=row.horario_realizado,
        status=row.status, lote=row.lote, observacao=row.observacao,
    )

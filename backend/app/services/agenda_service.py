"""Escala de diálise: vagas recorrentes por turno/dias/máquina + visão do dia."""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.core import Paciente
from ..models.hd import Escala
from ..schemas.auth import CurrentUser
from ..schemas.gestao import EscalaCreate, EscalaDiaOut, EscalaOut

TURNOS = ("manha", "tarde", "noite")


async def criar(
    session: AsyncSession, paciente_id: str, body: EscalaCreate, user: CurrentUser
) -> EscalaOut:
    if body.turno not in TURNOS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "turno inválido")
    if any(d < 1 or d > 7 for d in body.dias_semana):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "dias_semana usa ISO 1 (segunda) a 7 (domingo)")

    # Conflito de máquina: mesma unidade + turno + máquina com dia em comum
    if body.maquina:
        existentes = await session.scalars(
            select(Escala).where(
                Escala.unidade_id == user.unidade_id,
                Escala.turno == body.turno,
                Escala.maquina == body.maquina,
                Escala.ativo.is_(True),
            )
        )
        dias_novos = set(body.dias_semana)
        for e in existentes:
            conflito = dias_novos & set(e.dias_semana)
            if conflito:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"máquina {body.maquina} já ocupada no turno {body.turno} "
                    f"(dias {sorted(conflito)})",
                )

    escala = Escala(
        paciente_id=paciente_id, unidade_id=user.unidade_id,
        turno=body.turno, dias_semana=sorted(set(body.dias_semana)),
        maquina=body.maquina,
    )
    session.add(escala)
    await session.commit()
    return await _to_out(session, escala)


async def listar(session: AsyncSession, unidade_id: str) -> list[EscalaOut]:
    rows = await session.scalars(
        select(Escala).where(Escala.unidade_id == unidade_id, Escala.ativo.is_(True))
        .order_by(Escala.turno, Escala.maquina)
    )
    return [await _to_out(session, e) for e in rows]


async def escala_do_dia(
    session: AsyncSession, unidade_id: str, data: dt.date
) -> EscalaDiaOut:
    """Quem é esperado na sala em `data`, agrupado por turno."""
    dia_iso = data.isoweekday()
    rows = await session.scalars(
        select(Escala).where(Escala.unidade_id == unidade_id, Escala.ativo.is_(True))
    )
    turnos: dict[str, list[EscalaOut]] = {t: [] for t in TURNOS}
    for e in rows:
        if dia_iso in e.dias_semana:
            turnos[e.turno].append(await _to_out(session, e))
    for lista in turnos.values():
        lista.sort(key=lambda v: (v.maquina or "", v.paciente_nome or ""))
    return EscalaDiaOut(data=data, dia_semana=dia_iso, turnos=turnos)


async def _to_out(session: AsyncSession, e: Escala) -> EscalaOut:
    paciente = await session.get(Paciente, e.paciente_id)
    return EscalaOut(
        id=e.id, paciente_id=e.paciente_id,
        paciente_nome=paciente.nome if paciente else None,
        turno=e.turno, dias_semana=list(e.dias_semana),
        maquina=e.maquina, ativo=e.ativo,
    )

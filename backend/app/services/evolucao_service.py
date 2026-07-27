"""Regras de evolução clínica (SOAP): criação, listagem e assinatura."""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.clinico import Evolucao
from ..schemas.auth import CurrentUser
from ..schemas.prontuario import EvolucaoCreate, EvolucaoOut


async def criar(
    session: AsyncSession, paciente_id: str, body: EvolucaoCreate, user: CurrentUser
) -> EvolucaoOut:
    if not any([body.subjetivo, body.objetivo, body.avaliacao, body.plano, body.texto_livre]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "evolução vazia")

    ev = Evolucao(
        paciente_id=paciente_id,
        profissional_id=user.profissional_id,
        episodio_id=body.episodio_id,
        categoria=body.categoria,
        subjetivo=body.subjetivo,
        objetivo=body.objetivo,
        avaliacao=body.avaliacao,
        plano=body.plano,
        texto_livre=body.texto_livre,
        # Assinatura fecha o documento (imutável). Sem step-up aqui: a API assume
        # que o cliente exigiu reautenticação antes de enviar assinar=True.
        assinada_em=dt.datetime.now(dt.timezone.utc) if body.assinar else None,
    )
    session.add(ev)
    await session.commit()
    await session.refresh(ev)
    return _to_out(ev)


async def listar(
    session: AsyncSession, paciente_id: str, categoria: str | None = None
) -> list[EvolucaoOut]:
    stmt = select(Evolucao).where(
        Evolucao.paciente_id == paciente_id, Evolucao.deleted_at.is_(None)
    )
    if categoria:
        stmt = stmt.where(Evolucao.categoria == categoria)
    stmt = stmt.order_by(Evolucao.created_at.desc())
    rows = await session.scalars(stmt)
    return [_to_out(ev) for ev in rows]


def _to_out(ev: Evolucao) -> EvolucaoOut:
    return EvolucaoOut(
        id=ev.id, categoria=ev.categoria, subjetivo=ev.subjetivo, objetivo=ev.objetivo,
        avaliacao=ev.avaliacao, plano=ev.plano, texto_livre=ev.texto_livre,
        resumo_ia=ev.resumo_ia, profissional_id=ev.profissional_id,
        assinada_em=ev.assinada_em, created_at=ev.created_at,
    )

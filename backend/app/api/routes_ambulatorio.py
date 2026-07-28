"""Rotas do ambulatório conservador: agenda de consultas + painel."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_authed_session, get_current_user, require_roles
from ..schemas.ambulatorio import (
    ConsultaCreate,
    ConsultaOut,
    ConsultaStatusRequest,
    PainelAmbulatorio,
)
from ..schemas.auth import CurrentUser
from ..services import ambulatorio_service

router = APIRouter(tags=["ambulatorio"])

_AGENDAM = ("medico", "enfermeiro", "administrativo", "equipe_multi", "admin")


@router.post("/pacientes/{paciente_id}/consultas",
             response_model=ConsultaOut, status_code=201)
async def agendar_consulta(
    paciente_id: uuid.UUID,
    body: ConsultaCreate,
    user: CurrentUser = Depends(require_roles(*_AGENDAM)),
    session: AsyncSession = Depends(get_authed_session),
):
    """Agenda consulta do ambulatório (primeira consulta, retorno, preparo TRS)."""
    return await ambulatorio_service.agendar(session, str(paciente_id), body, user)


@router.get("/ambulatorio/consultas", response_model=list[ConsultaOut])
async def agenda_do_dia(
    data: dt.date | None = None,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """Agenda do ambulatório no dia (padrão: hoje)."""
    return await ambulatorio_service.agenda_do_dia(
        session, str(user.unidade_id), data or dt.date.today())


@router.post("/consultas/{consulta_id}/status", response_model=ConsultaOut)
async def atualizar_status(
    consulta_id: uuid.UUID,
    body: ConsultaStatusRequest,
    user: CurrentUser = Depends(require_roles(*_AGENDAM)),
    session: AsyncSession = Depends(get_authed_session),
):
    """Fecha a consulta (realizada cria o episódio clínico na timeline)."""
    return await ambulatorio_service.atualizar_status(
        session, str(consulta_id), body, user)


@router.get("/ambulatorio/painel", response_model=PainelAmbulatorio)
async def painel(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """População conservadora por estágio + consultas + candidatos a preparo TRS."""
    return await ambulatorio_service.painel(session, str(user.unidade_id))

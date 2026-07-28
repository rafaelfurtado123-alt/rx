"""Rotas do prontuário: pacientes, header, timeline, evoluções e exames."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_authed_session, get_current_user, require_roles
from ..schemas.auth import CurrentUser
from ..schemas.prontuario import (
    EvolucaoCreate,
    EvolucaoOut,
    PacienteCreate,
    PacienteHeader,
    PacienteResumo,
    PacienteUpdate,
    ResumoIARequest,
    ResumoIAResponse,
    SerieExame,
    TimelineItem,
)
from ..services import evolucao_service, ia_service, prontuario_service

router = APIRouter(prefix="/pacientes", tags=["prontuario"])


@router.get("", response_model=list[PacienteResumo])
async def listar_pacientes(
    segmento: str | None = None,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """Pacientes da unidade, com filtro opcional por segmento
    (conservador | hemodialise | dialise_peritoneal | transplante)."""
    return await prontuario_service.listar_pacientes(
        session, str(user.unidade_id), segmento)


@router.post("", response_model=PacienteHeader, status_code=201)
async def criar_paciente(
    body: PacienteCreate,
    user: CurrentUser = Depends(
        require_roles("medico", "enfermeiro", "administrativo", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Cadastro do paciente renal (ambulatório conservador ou hemodiálise)."""
    return await prontuario_service.criar_paciente(session, body, user)


@router.patch("/{paciente_id}", response_model=PacienteHeader)
async def atualizar_paciente(
    paciente_id: uuid.UUID,
    body: PacienteUpdate,
    _: CurrentUser = Depends(
        require_roles("medico", "enfermeiro", "administrativo", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Atualiza o cadastro — inclui a transição conservador → hemodiálise."""
    return await prontuario_service.atualizar_paciente(
        session, str(paciente_id), body)


@router.get("/{paciente_id}", response_model=PacienteHeader)
async def header(
    paciente_id: uuid.UUID,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await prontuario_service.get_header(session, str(paciente_id))


@router.get("/{paciente_id}/timeline", response_model=list[TimelineItem])
async def timeline(
    paciente_id: uuid.UUID,
    limite: int = 50,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await prontuario_service.timeline(session, str(paciente_id), limite)


@router.get("/{paciente_id}/exames/{codigo}", response_model=SerieExame)
async def serie_exame(
    paciente_id: uuid.UUID,
    codigo: str,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await prontuario_service.serie_exame(session, str(paciente_id), codigo.upper())


@router.get("/{paciente_id}/evolucoes", response_model=list[EvolucaoOut])
async def listar_evolucoes(
    paciente_id: uuid.UUID,
    categoria: str | None = None,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await evolucao_service.listar(session, str(paciente_id), categoria)


@router.post("/{paciente_id}/evolucoes", response_model=EvolucaoOut, status_code=201)
async def criar_evolucao(
    paciente_id: uuid.UUID,
    body: EvolucaoCreate,
    # Perfis assistenciais registram evolução (inclui equipe multiprofissional)
    user: CurrentUser = Depends(
        require_roles("medico", "enfermeiro", "tecnico", "equipe_multi", "admin")
    ),
    session: AsyncSession = Depends(get_authed_session),
):
    return await evolucao_service.criar(session, str(paciente_id), body, user)


@router.post("/{paciente_id}/evolucoes/resumo-ia", response_model=ResumoIAResponse)
async def resumo_ia(
    paciente_id: uuid.UUID,
    body: ResumoIARequest,
    _: CurrentUser = Depends(
        require_roles("medico", "enfermeiro", "equipe_multi", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Rascunho de sumarização por IA — SEMPRE revisável antes de assinar."""
    return ResumoIAResponse(resumo=ia_service.summarize_soap(body), rascunho=True)

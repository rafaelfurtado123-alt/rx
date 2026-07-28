"""Rotas de prescrição eletrônica (geral + HD) e sessão de hemodiálise."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_authed_session, get_current_user, require_roles
from ..schemas.auth import CurrentUser
from ..schemas.hd import (
    AcessoCreate,
    AcessoOut,
    EncerramentoRequest,
    IntercorrenciaRequest,
    ParametroRequest,
    PrescricaoCreate,
    PrescricaoHDCreate,
    PrescricaoHDOut,
    PrescricaoOut,
    RecepcaoRequest,
    SessaoOut,
)
from ..services import hd_service, prescricao_service

router = APIRouter(tags=["hd"])

# ------------------------- Prescrição geral -------------------------


@router.post("/pacientes/{paciente_id}/prescricoes",
             response_model=PrescricaoOut, status_code=201)
async def criar_prescricao(
    paciente_id: uuid.UUID,
    body: PrescricaoCreate,
    # Prescrever é ato médico (SAE fica com enfermagem)
    user: CurrentUser = Depends(require_roles("medico", "enfermeiro", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    return await prescricao_service.criar(session, str(paciente_id), body, user)


@router.get("/pacientes/{paciente_id}/prescricoes",
            response_model=list[PrescricaoOut])
async def listar_prescricoes(
    paciente_id: uuid.UUID,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await prescricao_service.listar(session, str(paciente_id))


# ------------------------- Acesso vascular -------------------------


@router.post("/pacientes/{paciente_id}/acessos",
             response_model=AcessoOut, status_code=201)
async def criar_acesso(
    paciente_id: uuid.UUID,
    body: AcessoCreate,
    _: CurrentUser = Depends(require_roles("medico", "enfermeiro", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    return await hd_service.criar_acesso(session, str(paciente_id), body)


@router.get("/pacientes/{paciente_id}/acessos", response_model=list[AcessoOut])
async def listar_acessos(
    paciente_id: uuid.UUID,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await hd_service.listar_acessos(session, str(paciente_id))


# ------------------------- Prescrição de HD -------------------------


@router.post("/pacientes/{paciente_id}/prescricoes-hd",
             response_model=PrescricaoHDOut, status_code=201)
async def criar_prescricao_hd(
    paciente_id: uuid.UUID,
    body: PrescricaoHDCreate,
    user: CurrentUser = Depends(require_roles("medico", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Prescrição de HD completa (nível Tasy) com validações clínicas cruzadas."""
    return await hd_service.criar_prescricao_hd(session, str(paciente_id), body, user)


@router.get("/pacientes/{paciente_id}/prescricoes-hd",
            response_model=list[PrescricaoHDOut])
async def listar_prescricoes_hd(
    paciente_id: uuid.UUID,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await hd_service.listar_prescricoes_hd(session, str(paciente_id))


# ------------------------- Sessão de HD -------------------------


@router.post("/pacientes/{paciente_id}/sessoes",
             response_model=SessaoOut, status_code=201)
async def recepcao(
    paciente_id: uuid.UUID,
    body: RecepcaoRequest,
    user: CurrentUser = Depends(
        require_roles("medico", "enfermeiro", "tecnico", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Recepção do paciente: peso pré, PA, FC, Tª, queixas (cria a sessão)."""
    return await hd_service.recepcao(session, str(paciente_id), body, user)


@router.get("/pacientes/{paciente_id}/sessoes", response_model=list[SessaoOut])
async def listar_sessoes(
    paciente_id: uuid.UUID,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await hd_service.listar_sessoes(session, str(paciente_id))


@router.post("/sessoes/{sessao_id}/iniciar", response_model=SessaoOut)
async def iniciar_sessao(
    sessao_id: uuid.UUID,
    maquina: str | None = None,
    user: CurrentUser = Depends(
        require_roles("medico", "enfermeiro", "tecnico", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    return await hd_service.iniciar(session, str(sessao_id), maquina, user)


@router.post("/sessoes/{sessao_id}/parametros", status_code=201)
async def registrar_parametro(
    sessao_id: uuid.UUID,
    body: ParametroRequest,
    _: CurrentUser = Depends(
        require_roles("medico", "enfermeiro", "tecnico", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Registro intradialítico (PA, FC, PTM, fluxo de UF) — monitor em tempo real."""
    return await hd_service.registrar_parametro(session, str(sessao_id), body)


@router.post("/sessoes/{sessao_id}/intercorrencias", status_code=201)
async def registrar_intercorrencia(
    sessao_id: uuid.UUID,
    body: IntercorrenciaRequest,
    user: CurrentUser = Depends(
        require_roles("medico", "enfermeiro", "tecnico", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    return await hd_service.registrar_intercorrencia(session, str(sessao_id), body, user)


@router.post("/sessoes/{sessao_id}/encerrar", response_model=SessaoOut)
async def encerrar_sessao(
    sessao_id: uuid.UUID,
    body: EncerramentoRequest,
    _: CurrentUser = Depends(
        require_roles("medico", "enfermeiro", "tecnico", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Encerramento: peso pós/UF real + Kt/V, URR e nPCR automáticos."""
    return await hd_service.encerrar(session, str(sessao_id), body)

"""Rotas de autenticação (login em 2 passos + 2FA + contexto)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..services import auth_service
from ..schemas.auth import (
    LoginRequest,
    LoginResponse,
    SelectContextRequest,
    TokenResponse,
    TotpEnrollResponse,
    Verify2FARequest,
    Verify2FAResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    """Passo 1 — valida senha; devolve token intermediário de 2FA."""
    return await auth_service.login(session, body.email, body.senha)


@router.post("/2fa/enroll", response_model=TotpEnrollResponse)
async def enroll_totp(mfa_token: str, session: AsyncSession = Depends(get_session)):
    """Primeiro acesso — gera segredo TOTP (QR via otpauth_uri)."""
    return await auth_service.enroll_totp(session, mfa_token)


@router.post("/2fa/verify", response_model=Verify2FAResponse)
async def verify_2fa(body: Verify2FARequest, session: AsyncSession = Depends(get_session)):
    """Passo 2 — confere o código TOTP; devolve refresh + vínculos."""
    return await auth_service.verify_2fa(session, body.mfa_token, body.codigo)


@router.post("/context", response_model=TokenResponse)
async def select_context(
    body: SelectContextRequest, session: AsyncSession = Depends(get_session)
):
    """Escolhe unidade+papel ativos; emite o access token com o contexto."""
    return await auth_service.select_context(
        session, body.refresh_token, str(body.unidade_id), body.papel
    )


# ---------------- Login por certificado digital (VIDaaS/CRM Digital) ----------------


@router.post("/vidaas/login", status_code=201)
async def vidaas_login(body: dict, session: AsyncSession = Depends(get_session)):
    """Inicia o login por certificado em nuvem — body: {"cpf": "..."}."""
    return await auth_service.vidaas_login_iniciar(session, body.get("cpf", ""))


@router.get("/vidaas/login/{state}")
async def vidaas_login_status(state: str,
                              session: AsyncSession = Depends(get_session)):
    """Polling: {status} enquanto pendente; quando autorizada, consome a
    sessão e devolve {refresh_token, vinculos} (mesmo formato do 2FA)."""
    return await auth_service.vidaas_login_status(session, state)

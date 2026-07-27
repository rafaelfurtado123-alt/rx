"""Regras de autenticação: login em 2 passos, 2FA e seleção de contexto."""
from __future__ import annotations

import datetime as dt

import jwt
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import security
from ..models.core import Profissional, Vinculo
from ..schemas.auth import (
    LoginResponse,
    TokenResponse,
    TotpEnrollResponse,
    Verify2FAResponse,
    VinculoOut,
)


async def _get_by_email(session: AsyncSession, email: str) -> Profissional | None:
    return await session.scalar(
        select(Profissional).where(Profissional.email == email.lower())
    )


async def login(session: AsyncSession, email: str, senha: str) -> LoginResponse:
    """Passo 1: valida e-mail + senha. Mensagem genérica evita enumeração de usuários."""
    prof = await _get_by_email(session, email)
    generic = HTTPException(status.HTTP_401_UNAUTHORIZED, "credenciais inválidas")
    if prof is None or not prof.ativo or not prof.senha_hash:
        # Ainda assim gastamos tempo verificando um hash dummy? Simplificado aqui.
        raise generic
    if not security.verify_password(senha, prof.senha_hash):
        raise generic

    # Reidrata o hash se os parâmetros do Argon2 mudaram
    if security.needs_rehash(prof.senha_hash):
        prof.senha_hash = security.hash_password(senha)
        await session.commit()

    mfa_token = security.create_mfa_token(str(prof.id))
    return LoginResponse(
        mfa_required=True,
        mfa_token=mfa_token,
        totp_enrollment_required=not prof.totp_ativo,
    )


async def enroll_totp(session: AsyncSession, mfa_token: str) -> TotpEnrollResponse:
    """Gera segredo TOTP no primeiro acesso (2FA obrigatório para perfis clínicos)."""
    prof = await _prof_from_mfa(session, mfa_token)
    secret = security.generate_totp_secret()
    prof.totp_secret = secret  # cifrar em produção (pgcrypto/KMS)
    await session.commit()
    uri = security.totp_provisioning_uri(secret, prof.email or prof.nome)
    return TotpEnrollResponse(secret=secret, otpauth_uri=uri)


async def verify_2fa(session: AsyncSession, mfa_token: str, codigo: str) -> Verify2FAResponse:
    """Passo 2: confere o código TOTP e devolve refresh + vínculos disponíveis."""
    prof = await _prof_from_mfa(session, mfa_token)
    if not prof.totp_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "2FA não configurado")
    if not security.verify_totp(prof.totp_secret, codigo):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "código 2FA inválido")

    if not prof.totp_ativo:
        prof.totp_ativo = True
    prof.ultimo_login = dt.datetime.now(dt.timezone.utc)
    await session.commit()

    vinculos = await session.scalars(
        select(Vinculo).where(Vinculo.profissional_id == prof.id, Vinculo.ativo.is_(True))
    )
    saida = [
        VinculoOut(unidade_id=v.unidade_id, unidade_nome=v.unidade.nome, papel=v.papel)
        for v in vinculos
    ]
    if not saida:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "sem vínculo ativo em nenhuma unidade")

    return Verify2FAResponse(
        refresh_token=security.create_refresh_token(str(prof.id)),
        vinculos=saida,
    )


async def select_context(
    session: AsyncSession, refresh_token: str, unidade_id: str, papel: str
) -> TokenResponse:
    """Escolhe unidade+papel ativos e emite o access token com esse contexto."""
    prof = await _prof_from_refresh(session, refresh_token)
    vinculo = await session.scalar(
        select(Vinculo).where(
            Vinculo.profissional_id == prof.id,
            Vinculo.unidade_id == unidade_id,
            Vinculo.papel == papel,
            Vinculo.ativo.is_(True),
        )
    )
    if vinculo is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "vínculo inválido para o contexto")

    access = security.create_access_token(str(prof.id), str(unidade_id), papel, prof.nome)
    return TokenResponse(
        access_token=access,
        refresh_token=security.create_refresh_token(str(prof.id)),
        unidade_id=unidade_id,
        papel=papel,
    )


# --------------------------- helpers de token ---------------------------
async def _prof_from_token(session: AsyncSession, token: str, ttype) -> Profissional:
    try:
        payload = security.decode_token(token, ttype)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token inválido")
    prof = await session.get(Profissional, payload["sub"])
    if prof is None or not prof.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "profissional inválido")
    return prof


async def _prof_from_mfa(session: AsyncSession, token: str) -> Profissional:
    return await _prof_from_token(session, token, "mfa")


async def _prof_from_refresh(session: AsyncSession, token: str) -> Profissional:
    return await _prof_from_token(session, token, "refresh")

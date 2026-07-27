"""Dependências FastAPI: usuário autenticado, RBAC e sessão com contexto RLS."""
from __future__ import annotations

from collections.abc import AsyncIterator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.core import Profissional
from ..schemas.auth import CurrentUser
from .database import SessionLocal, set_rls_context
from .security import decode_token

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> CurrentUser:
    """Valida o access token e devolve o usuário + contexto ativo (unidade/papel)."""
    try:
        payload = decode_token(creds.credentials, "access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token inválido")

    unidade = payload.get("unidade_id")
    papel = payload.get("papel")
    if not unidade or not papel:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "contexto (unidade/papel) não selecionado"
        )
    # nome é opcional aqui; carregado sob demanda quando necessário
    return CurrentUser(
        profissional_id=payload["sub"],
        nome=payload.get("nome", ""),
        unidade_id=unidade,
        papel=papel,
    )


async def get_authed_session(
    user: CurrentUser = Depends(get_current_user),
) -> AsyncIterator[AsyncSession]:
    """Sessão de banco COM contexto RLS/auditoria definido para o usuário atual."""
    async with SessionLocal() as session:
        await set_rls_context(session, str(user.profissional_id))
        yield session


def require_roles(*roles: str):
    """Fábrica de dependência RBAC: exige que o papel ativo esteja em `roles`."""

    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.papel not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"perfil '{user.papel}' sem permissão (requer: {', '.join(roles)})",
            )
        return user

    return _checker


async def load_profissional(
    session: AsyncSession, profissional_id: str
) -> Profissional | None:
    return await session.scalar(
        select(Profissional).where(Profissional.id == profissional_id)
    )

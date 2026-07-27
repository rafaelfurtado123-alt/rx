"""Camada de banco: engine assíncrono + sessão com contexto de RLS/auditoria.

Como o auth é próprio da API, o RLS do Postgres é dirigido por GUCs de sessão:
    * ``app.profissional_id`` — usado pelas policies (ver db/rls_fastapi_context.sql)
    * ``app.ator_id``         — usado pelo trigger de auditoria (hash-chain)

Cada requisição autenticada define esses GUCs na transação, garantindo que o RLS
continue sendo a última linha de defesa mesmo que a API falhe.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .config import get_settings

_settings = get_settings()

# Em testes cada teste roda em seu próprio event loop; NullPool evita reuso de
# conexões asyncpg entre loops (fonte clássica de erros). Em produção, pooling normal.
_engine_kwargs: dict = {"echo": _settings.debug}
if _settings.environment == "test":
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(_settings.database_url, **_engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Sessão sem contexto de usuário (rotas públicas: login)."""
    async with SessionLocal() as session:
        yield session


async def set_rls_context(session: AsyncSession, profissional_id: str) -> None:
    """Define os GUCs locais à transação para RLS + auditoria."""
    await session.execute(
        text("select set_config('app.profissional_id', :pid, true), "
             "set_config('app.ator_id', :pid, true)"),
        {"pid": profissional_id},
    )

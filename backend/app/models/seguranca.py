"""Modelos ORM do schema `seguranca` usados pela assinatura digital."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Assinatura(Base):
    """Assinatura eletrônica/ICP-Brasil de um documento (evolução, prescrição, LME)."""
    __tablename__ = "assinatura"
    __table_args__ = {"schema": "seguranca"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    entidade: Mapped[str] = mapped_column(Text)          # 'lme' | 'prescricao' | ...
    entidade_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    assinante_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.profissional.id"))
    hash_conteudo: Mapped[str] = mapped_column(Text)     # SHA-256 hex do documento
    tipo: Mapped[str] = mapped_column(Text, default="eletronica")  # | icp_brasil
    certificado: Mapped[dict | None] = mapped_column(JSONB)
    assinatura_b64: Mapped[str | None] = mapped_column(Text)  # CMS/PKCS#7 destacada
    documento_b64: Mapped[str | None] = mapped_column(Text)   # PDF exato assinado
    assinado_em: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )


class VidaasSessao(Base):
    """Sessão de autorização OAuth2/PKCE junto ao PSC (VIDaaS)."""
    __tablename__ = "vidaas_sessao"
    __table_args__ = {"schema": "seguranca"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    profissional_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("core.profissional.id")
    )
    state: Mapped[str] = mapped_column(Text, unique=True)
    code_verifier: Mapped[str] = mapped_column(Text)
    access_token: Mapped[str | None] = mapped_column(Text)  # cifrar em produção
    token_expira_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, default="pendente")
    finalidade: Mapped[str] = mapped_column(Text, default="assinatura")  # | login
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

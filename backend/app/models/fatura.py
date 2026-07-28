"""Modelos ORM do faturamento (schema `fatura`) + tabela SIGTAP (schema `ref`)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RefSigtap(Base):
    """Procedimentos SUS (tabela SIGTAP) — usada nos itens de conta."""
    __tablename__ = "sigtap"
    __table_args__ = {"schema": "ref"}

    codigo: Mapped[str] = mapped_column(String(15), primary_key=True)
    descricao: Mapped[str] = mapped_column(Text)
    valor_sus: Mapped[float | None] = mapped_column(Numeric)


class Conta(Base):
    """Conta de produção mensal (competência) por paciente."""
    __tablename__ = "conta"
    __table_args__ = {"schema": "fatura"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.paciente.id"))
    unidade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.unidade.id"))
    competencia: Mapped[dt.date] = mapped_column(Date)
    tipo: Mapped[str] = mapped_column(Text, default="sus")
    status: Mapped[str] = mapped_column(Text, default="aberta")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )


class ContaItem(Base):
    __tablename__ = "conta_item"
    __table_args__ = {"schema": "fatura"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    conta_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fatura.conta.id", ondelete="CASCADE")
    )
    sigtap_codigo: Mapped[str | None] = mapped_column(
        String(15), ForeignKey("ref.sigtap.codigo")
    )
    quantidade: Mapped[int] = mapped_column(Integer, default=1)
    valor: Mapped[float | None] = mapped_column(Numeric)


class Apac(Base):
    """APAC — Autorização de Procedimento de Alta Complexidade (TRS)."""
    __tablename__ = "apac"
    __table_args__ = {"schema": "fatura"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.paciente.id"))
    numero: Mapped[str | None] = mapped_column(String(20))
    competencia: Mapped[dt.date] = mapped_column(Date)
    procedimento: Mapped[str | None] = mapped_column(String(15))
    cid: Mapped[str | None] = mapped_column(String(10))
    validade_ini: Mapped[dt.date | None] = mapped_column(Date)
    validade_fim: Mapped[dt.date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text, default="ativa")

"""Modelos ORM do LME (schema `lme`) + catálogo de PCDT (schema `ref`)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

STATUS_LAUDO = ("rascunho", "emitido", "assinado", "vigente", "vencido",
                "renovado", "negado", "cancelado")


class RefPcdt(Base):
    """Protocolo clínico (PCDT) versionado — coração do motor de LME."""
    __tablename__ = "pcdt"
    __table_args__ = {"schema": "ref"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(Text)
    versao: Mapped[str] = mapped_column(Text)
    vigencia_ini: Mapped[dt.date] = mapped_column(Date)
    vigencia_fim: Mapped[dt.date | None] = mapped_column(Date)
    regras_json: Mapped[dict] = mapped_column(JSONB)


class Laudo(Base):
    __tablename__ = "laudo"
    __table_args__ = {"schema": "lme"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.paciente.id"))
    medico_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.profissional.id"))
    unidade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.unidade.id"))
    pcdt_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ref.pcdt.id"))
    # FK para ref.cid10 garantida pelo banco; sem espelho ORM (tabela não mapeada)
    cid_principal: Mapped[str | None] = mapped_column(String(10))
    cids_secundarios: Mapped[list[str] | None] = mapped_column(ARRAY(String(10)))
    anamnese: Mapped[str | None] = mapped_column(Text)
    justificativa: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        SAEnum(*STATUS_LAUDO, name="status_laudo", schema="lme", create_type=False),
        default="rascunho",
    )
    emitido_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    valido_ate: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    laudo_anterior_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lme.laudo.id")
    )
    pdf_storage_path: Mapped[str | None] = mapped_column(Text)
    assinatura_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ia_metadados: Mapped[dict | None] = mapped_column(JSONB)


class LaudoItem(Base):
    __tablename__ = "item"
    __table_args__ = {"schema": "lme"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    laudo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lme.laudo.id", ondelete="CASCADE")
    )
    medicamento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ref.medicamento.id"))
    cid: Mapped[str | None] = mapped_column(String(10))
    posologia: Mapped[str | None] = mapped_column(Text)
    quantidade_mes: Mapped[float | None] = mapped_column(Numeric)
    unidade: Mapped[str | None] = mapped_column(Text)


class ExameVinculado(Base):
    """Exames obrigatórios do PCDT × resultado usado no laudo."""
    __tablename__ = "exame_vinculado"
    __table_args__ = {"schema": "lme"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    laudo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lme.laudo.id", ondelete="CASCADE")
    )
    exame_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ref.exame.id"))
    exame_resultado_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clinico.exame_resultado.id")
    )
    obrigatorio: Mapped[bool] = mapped_column(Boolean, default=True)
    situacao: Mapped[str] = mapped_column(Text, default="ausente")


class Termo(Base):
    """Termo de Esclarecimento e Responsabilidade (TER) do laudo."""
    __tablename__ = "termo"
    __table_args__ = {"schema": "lme"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    laudo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lme.laudo.id", ondelete="CASCADE"), unique=True
    )
    versao: Mapped[str] = mapped_column(Text)
    texto: Mapped[str] = mapped_column(Text)
    aceite_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    aceite_por: Mapped[str | None] = mapped_column(Text)
    assinatura_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

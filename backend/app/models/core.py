"""Modelos ORM do schema `core` (subconjunto usado por Auth + Dashboard)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

PAPEIS = ("medico", "enfermeiro", "tecnico", "administrativo", "admin", "auditor",
          "paciente", "equipe_multi")
SEXOS = ("masculino", "feminino", "intersexo", "nao_informado")
SEGMENTOS = ("conservador", "hemodialise", "dialise_peritoneal", "transplante")


class Unidade(Base):
    __tablename__ = "unidade"
    __table_args__ = {"schema": "core"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    cnes: Mapped[str | None] = mapped_column(String(7), unique=True)
    tipo: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Profissional(Base):
    __tablename__ = "profissional"
    __table_args__ = {"schema": "core"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(11), unique=True)
    conselho_tipo: Mapped[str | None] = mapped_column(Text)
    conselho_num: Mapped[str | None] = mapped_column(Text)
    conselho_uf: Mapped[str | None] = mapped_column(String(2))
    especialidade: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    # Credenciais (auth próprio) — ver db/auth_fastapi_columns.sql
    senha_hash: Mapped[str | None] = mapped_column(Text)
    totp_secret: Mapped[str | None] = mapped_column(Text)
    totp_ativo: Mapped[bool] = mapped_column(Boolean, default=False)
    ultimo_login: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    vinculos: Mapped[list["Vinculo"]] = relationship(
        back_populates="profissional", lazy="selectin"
    )


class Vinculo(Base):
    __tablename__ = "vinculo"
    __table_args__ = {"schema": "core"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    profissional_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("core.profissional.id"), nullable=False
    )
    unidade_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("core.unidade.id"), nullable=False
    )
    papel: Mapped[str] = mapped_column(
        SAEnum(*PAPEIS, name="tipo_papel", schema="core", create_type=False),
        nullable=False,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    profissional: Mapped[Profissional] = relationship(back_populates="vinculos")
    unidade: Mapped[Unidade] = relationship(lazy="joined")


class Paciente(Base):
    __tablename__ = "paciente"
    __table_args__ = {"schema": "core"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    nome_social: Mapped[str | None] = mapped_column(Text)
    cns: Mapped[str | None] = mapped_column(String(15), unique=True)
    cpf: Mapped[str | None] = mapped_column(String(11), unique=True)
    sexo: Mapped[str] = mapped_column(
        SAEnum(*SEXOS, name="sexo", schema="core", create_type=False),
        default="nao_informado",
    )
    data_nascimento: Mapped[dt.date | None] = mapped_column(Date)
    etiologia_drc: Mapped[str | None] = mapped_column(Text)
    estagio_drc: Mapped[int | None] = mapped_column()
    # Segmento de cuidado: ambulatório conservador × TRS (HD/DP) × transplante
    segmento: Mapped[str] = mapped_column(Text, default="hemodialise")
    inicio_trs: Mapped[dt.date | None] = mapped_column(Date)
    turno_dialise: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class PacienteUnidade(Base):
    __tablename__ = "paciente_unidade"
    __table_args__ = {"schema": "core"}

    paciente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("core.paciente.id"), primary_key=True
    )
    unidade_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("core.unidade.id"), primary_key=True
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

"""Modelos ORM do prontuário longitudinal (schema `clinico`) + referência de exames."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

TIPO_EPISODIO = ("consulta", "sessao_hd", "internacao", "intercorrencia",
                 "telemedicina", "procedimento")
CATEGORIA_EVOLUCAO = ("medica", "enfermagem", "nutricao", "servico_social",
                      "psicologia", "farmacia", "fisioterapia")


class Episodio(Base):
    __tablename__ = "episodio"
    __table_args__ = {"schema": "clinico"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.paciente.id"))
    unidade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.unidade.id"))
    tipo: Mapped[str] = mapped_column(
        SAEnum(*TIPO_EPISODIO, name="tipo_episodio", schema="clinico", create_type=False)
    )
    inicio: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    fim: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("core.profissional.id")
    )
    resumo: Mapped[str | None] = mapped_column(Text)


class Evolucao(Base):
    __tablename__ = "evolucao"
    __table_args__ = {"schema": "clinico"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    episodio_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clinico.episodio.id")
    )
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.paciente.id"))
    profissional_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.profissional.id"))
    categoria: Mapped[str] = mapped_column(
        SAEnum(*CATEGORIA_EVOLUCAO, name="categoria_evolucao", schema="clinico",
               create_type=False),
        default="medica",
    )
    subjetivo: Mapped[str | None] = mapped_column(Text)
    objetivo: Mapped[str | None] = mapped_column(Text)
    avaliacao: Mapped[str | None] = mapped_column(Text)
    plano: Mapped[str | None] = mapped_column(Text)
    texto_livre: Mapped[str | None] = mapped_column(Text)
    resumo_ia: Mapped[str | None] = mapped_column(Text)
    assinada_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class ExameResultado(Base):
    __tablename__ = "exame_resultado"
    __table_args__ = {"schema": "clinico"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.paciente.id"))
    exame_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ref.exame.id"))
    valor: Mapped[float | None] = mapped_column(Numeric)
    valor_texto: Mapped[str | None] = mapped_column(Text)
    unidade: Mapped[str | None] = mapped_column(Text)
    data_coleta: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    fora_faixa: Mapped[bool | None] = mapped_column(Boolean)
    origem: Mapped[str | None] = mapped_column(Text)


class Alergia(Base):
    __tablename__ = "alergia"
    __table_args__ = {"schema": "clinico"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.paciente.id"))
    substancia: Mapped[str] = mapped_column(Text)
    reacao: Mapped[str | None] = mapped_column(Text)
    gravidade: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


STATUS_EMAR = ("previsto", "administrado", "recusado", "omitido", "adiado")


class ConsultaAgendada(Base):
    """Consulta do ambulatório conservador (agenda nefrológica)."""
    __tablename__ = "consulta_agendada"
    __table_args__ = {"schema": "clinico"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.paciente.id"))
    unidade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.unidade.id"))
    profissional_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("core.profissional.id")
    )
    data_hora: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    tipo: Mapped[str] = mapped_column(Text, default="retorno")
    status: Mapped[str] = mapped_column(Text, default="agendada")
    observacao: Mapped[str | None] = mapped_column(Text)
    episodio_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clinico.episodio.id")
    )


class Emar(Base):
    """Checagem eletrônica de administração de medicamentos (eMAR)."""
    __tablename__ = "emar"
    __table_args__ = {"schema": "clinico"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    prescricao_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinico.prescricao_item.id")
    )
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.paciente.id"))
    horario_previsto: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    horario_realizado: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    executante_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("core.profissional.id")
    )
    status: Mapped[str] = mapped_column(
        SAEnum(*STATUS_EMAR, name="status_emar", schema="clinico", create_type=False),
        default="previsto",
    )
    lote: Mapped[str | None] = mapped_column(Text)
    observacao: Mapped[str | None] = mapped_column(Text)


class RefExame(Base):
    """Catálogo de exames (schema ref) — usado para faixas de referência/gráficos."""
    __tablename__ = "exame"
    __table_args__ = {"schema": "ref"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    codigo: Mapped[str | None] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(Text)
    unidade: Mapped[str | None] = mapped_column(Text)
    ref_min: Mapped[float | None] = mapped_column(Numeric)
    ref_max: Mapped[float | None] = mapped_column(Numeric)
    categoria: Mapped[str | None] = mapped_column(Text)

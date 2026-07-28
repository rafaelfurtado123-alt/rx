"""Modelos ORM de prescrição (schema `clinico`) e hemodiálise (schema `hd`)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, Computed, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

TIPO_PRESCRICAO = ("geral", "hd", "enfermagem_sae")
STATUS_PRESCRICAO = ("rascunho", "ativa", "suspensa", "encerrada", "cancelada")
MODALIDADE_TRS = ("IHD", "SLED", "HDF_online", "CVVH", "CVVHD", "CVVHDF", "DPAC", "DPA")
TIPO_ACESSO = ("fav", "protese", "cateter_tunelizado", "cateter_temporario", "peritoneal")
STATUS_EMAR = ("previsto", "administrado", "recusado", "omitido", "adiado")


class RefMedicamento(Base):
    """Catálogo de medicamentos (schema ref) — base das checagens de prescrição."""
    __tablename__ = "medicamento"
    __table_args__ = {"schema": "ref"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    principio_ativo: Mapped[str] = mapped_column(Text)
    apresentacao: Mapped[str] = mapped_column(Text)
    via_padrao: Mapped[str | None] = mapped_column(Text)
    ceaf: Mapped[bool] = mapped_column(Boolean, default=False)
    requer_lme: Mapped[bool] = mapped_column(Boolean, default=False)
    ajuste_renal: Mapped[dict | None] = mapped_column(JSONB)
    dose_maxima_dia: Mapped[float | None] = mapped_column(Numeric)
    unidade_dose: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Prescricao(Base):
    __tablename__ = "prescricao"
    __table_args__ = {"schema": "clinico"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.paciente.id"))
    unidade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.unidade.id"))
    prescritor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.profissional.id"))
    tipo: Mapped[str] = mapped_column(
        SAEnum(*TIPO_PRESCRICAO, name="tipo_prescricao", schema="clinico",
               create_type=False)
    )
    status: Mapped[str] = mapped_column(
        SAEnum(*STATUS_PRESCRICAO, name="status_prescricao", schema="clinico",
               create_type=False),
        default="rascunho",
    )
    inicio: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    validade: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    assinada_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class PrescricaoItem(Base):
    __tablename__ = "prescricao_item"
    __table_args__ = {"schema": "clinico"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    prescricao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinico.prescricao.id", ondelete="CASCADE")
    )
    medicamento_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ref.medicamento.id")
    )
    descricao_livre: Mapped[str | None] = mapped_column(Text)
    dose: Mapped[float | None] = mapped_column(Numeric)
    unidade_dose: Mapped[str | None] = mapped_column(Text)
    via: Mapped[str | None] = mapped_column(Text)
    frequencia: Mapped[str | None] = mapped_column(Text)
    duracao: Mapped[str | None] = mapped_column(Text)
    ajuste_renal_aplicado: Mapped[bool | None] = mapped_column(Boolean, default=False)
    alertas: Mapped[dict | list | None] = mapped_column(JSONB)
    ordem: Mapped[int | None] = mapped_column(Integer)


class AcessoVascular(Base):
    __tablename__ = "acesso_vascular"
    __table_args__ = {"schema": "hd"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.paciente.id"))
    tipo: Mapped[str] = mapped_column(
        SAEnum(*TIPO_ACESSO, name="tipo_acesso", schema="hd", create_type=False)
    )
    lado: Mapped[str | None] = mapped_column(Text)
    localizacao: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="ativo")
    complicacoes: Mapped[str | None] = mapped_column(Text)


class PrescricaoHD(Base):
    """Prescrição de HD (1:1 com clinico.prescricao tipo 'hd') — campos nível Tasy."""
    __tablename__ = "prescricao_hd"
    __table_args__ = {"schema": "hd"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    prescricao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinico.prescricao.id", ondelete="CASCADE"), unique=True
    )
    modalidade: Mapped[str] = mapped_column(
        SAEnum(*MODALIDADE_TRS, name="modalidade_trs", schema="hd", create_type=False)
    )
    duracao_min: Mapped[int] = mapped_column(Integer)
    qb_ml_min: Mapped[int | None] = mapped_column(Integer)
    qd_ml_min: Mapped[int | None] = mapped_column(Integer)
    dialisador_modelo: Mapped[str | None] = mapped_column(Text)
    dialisador_reuso: Mapped[int | None] = mapped_column(Integer)
    acesso_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("hd.acesso_vascular.id")
    )
    ponto_puncao: Mapped[str | None] = mapped_column(Text)
    peso_atual_kg: Mapped[float | None] = mapped_column(Numeric)
    peso_seco_kg: Mapped[float | None] = mapped_column(Numeric)
    uf_prescrita_l: Mapped[float | None] = mapped_column(Numeric)
    uf_maxima_l: Mapped[float | None] = mapped_column(Numeric)
    perfil_sodio: Mapped[dict | None] = mapped_column(JSONB)
    perfil_bicarbonato: Mapped[dict | None] = mapped_column(JSONB)
    condutividade: Mapped[float | None] = mapped_column(Numeric)
    temperatura_banho: Mapped[float | None] = mapped_column(Numeric)
    heparinizacao: Mapped[dict | None] = mapped_column(JSONB)
    solucoes_json: Mapped[list | dict | None] = mapped_column(JSONB)
    # Coluna GERADA no banco (peso_atual − peso_seco) — somente leitura.
    volume_calculado_l: Mapped[float | None] = mapped_column(
        Numeric,
        Computed("greatest(coalesce(peso_atual_kg,0) - coalesce(peso_seco_kg,0), 0)",
                 persisted=True),
    )


class SessaoHD(Base):
    __tablename__ = "sessao"
    __table_args__ = {"schema": "hd"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.paciente.id"))
    unidade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.unidade.id"))
    prescricao_hd_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("hd.prescricao_hd.id")
    )
    acesso_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("hd.acesso_vascular.id")
    )
    episodio_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clinico.episodio.id")
    )
    # Recepção
    peso_pre_kg: Mapped[float | None] = mapped_column(Numeric)
    pa_pre: Mapped[str | None] = mapped_column(Text)
    fc_pre: Mapped[int | None] = mapped_column(Integer)
    temp_pre: Mapped[float | None] = mapped_column(Numeric)
    queixas: Mapped[str | None] = mapped_column(Text)
    # Execução
    inicio: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    fim: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    maquina: Mapped[str | None] = mapped_column(Text)
    tecnico_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("core.profissional.id")
    )
    enfermeiro_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("core.profissional.id")
    )
    # Encerramento
    peso_pos_kg: Mapped[float | None] = mapped_column(Numeric)
    uf_real_l: Mapped[float | None] = mapped_column(Numeric)
    pa_pos: Mapped[str | None] = mapped_column(Text)
    fc_pos: Mapped[int | None] = mapped_column(Integer)
    # Adequação (calculada)
    ktv: Mapped[float | None] = mapped_column(Numeric)
    urr: Mapped[float | None] = mapped_column(Numeric)
    npcr: Mapped[float | None] = mapped_column(Numeric)
    intercorrencias_resumo: Mapped[str | None] = mapped_column(Text)


class SessaoParametro(Base):
    """Série temporal intradialítica (monitor em tempo real)."""
    __tablename__ = "sessao_parametro"
    __table_args__ = {"schema": "hd"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    sessao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hd.sessao.id", ondelete="CASCADE")
    )
    ts: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    pa: Mapped[str | None] = mapped_column(Text)
    fc: Mapped[int | None] = mapped_column(Integer)
    qb_ml_min: Mapped[int | None] = mapped_column(Integer)
    ptm: Mapped[float | None] = mapped_column(Numeric)
    fluxo_uf: Mapped[float | None] = mapped_column(Numeric)
    condutividade: Mapped[float | None] = mapped_column(Numeric)
    temperatura: Mapped[float | None] = mapped_column(Numeric)


class Intercorrencia(Base):
    __tablename__ = "intercorrencia"
    __table_args__ = {"schema": "hd"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    sessao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hd.sessao.id", ondelete="CASCADE")
    )
    ts: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    tipo: Mapped[str] = mapped_column(Text)
    descricao: Mapped[str | None] = mapped_column(Text)
    conduta: Mapped[str | None] = mapped_column(Text)
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("core.profissional.id")
    )

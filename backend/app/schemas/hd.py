"""DTOs de prescrição (geral + HD) e sessão de hemodiálise."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field


# ------------------------- Prescrição geral -------------------------
class ItemCreate(BaseModel):
    medicamento_id: uuid.UUID | None = None
    descricao_livre: str | None = None
    dose: float | None = None
    unidade_dose: str | None = None
    via: str | None = None
    frequencia: str | None = None
    duracao: str | None = None


class AlertaItem(BaseModel):
    tipo: str  # 'alergia' | 'dose_maxima' | 'ajuste_renal' | 'interacao'
    gravidade: str  # 'bloqueio' | 'alerta' | 'info'
    mensagem: str


class ItemOut(BaseModel):
    id: uuid.UUID
    medicamento_id: uuid.UUID | None
    descricao_livre: str | None
    dose: float | None
    unidade_dose: str | None
    via: str | None
    frequencia: str | None
    duracao: str | None
    ajuste_renal_aplicado: bool | None
    alertas: list[AlertaItem] = []


class PrescricaoCreate(BaseModel):
    tipo: str = "geral"  # 'geral' | 'enfermagem_sae'
    itens: list[ItemCreate] = Field(min_length=1)
    assinar: bool = False


class PrescricaoOut(BaseModel):
    id: uuid.UUID
    tipo: str
    status: str
    assinada_em: dt.datetime | None
    itens: list[ItemOut] = []
    # Alertas de bloqueio impedem assinatura (ex.: alergia grave)
    bloqueada: bool = False


# ------------------------- Prescrição de HD -------------------------
class PrescricaoHDCreate(BaseModel):
    modalidade: str = "IHD"
    duracao_min: int = Field(gt=0, le=1440)
    qb_ml_min: int | None = Field(default=None, gt=0, le=600)
    qd_ml_min: int | None = Field(default=None, gt=0, le=1200)
    dialisador_modelo: str | None = None
    dialisador_reuso: int | None = None
    acesso_id: uuid.UUID | None = None
    ponto_puncao: str | None = None
    peso_atual_kg: float | None = Field(default=None, gt=0, le=400)
    peso_seco_kg: float | None = Field(default=None, gt=0, le=400)
    uf_prescrita_l: float | None = Field(default=None, ge=0, le=10)
    uf_maxima_l: float | None = Field(default=None, ge=0, le=10)
    perfil_sodio: dict | None = None
    perfil_bicarbonato: dict | None = None
    condutividade: float | None = None
    temperatura_banho: float | None = None
    heparinizacao: dict | None = None
    solucoes: list[dict] | None = None
    assinar: bool = False


class PrescricaoHDOut(BaseModel):
    id: uuid.UUID
    prescricao_id: uuid.UUID
    modalidade: str
    duracao_min: int
    qb_ml_min: int | None
    qd_ml_min: int | None
    dialisador_modelo: str | None
    acesso_id: uuid.UUID | None
    ponto_puncao: str | None
    peso_atual_kg: float | None
    peso_seco_kg: float | None
    uf_prescrita_l: float | None
    uf_maxima_l: float | None
    volume_calculado_l: float | None
    perfil_sodio: dict | None
    perfil_bicarbonato: dict | None
    heparinizacao: dict | None
    solucoes: list[dict] | None = None
    status: str
    assinada_em: dt.datetime | None
    alertas: list[AlertaItem] = []


# ------------------------- Acesso vascular -------------------------
class AcessoCreate(BaseModel):
    tipo: str
    lado: str | None = None
    localizacao: str | None = None


class AcessoOut(BaseModel):
    id: uuid.UUID
    tipo: str
    lado: str | None
    localizacao: str | None
    status: str


# ------------------------- Sessão de HD -------------------------
class RecepcaoRequest(BaseModel):
    prescricao_hd_id: uuid.UUID | None = None
    peso_pre_kg: float = Field(gt=0, le=400)
    pa_pre: str | None = None
    fc_pre: int | None = Field(default=None, gt=0, le=300)
    temp_pre: float | None = Field(default=None, ge=30, le=45)
    queixas: str | None = None


class ParametroRequest(BaseModel):
    pa: str | None = None
    fc: int | None = None
    qb_ml_min: int | None = None
    ptm: float | None = None
    fluxo_uf: float | None = None
    condutividade: float | None = None
    temperatura: float | None = None


class IntercorrenciaRequest(BaseModel):
    tipo: str
    descricao: str | None = None
    conduta: str | None = None


class EncerramentoRequest(BaseModel):
    peso_pos_kg: float = Field(gt=0, le=400)
    uf_real_l: float | None = Field(default=None, ge=0, le=10)
    pa_pos: str | None = None
    fc_pos: int | None = None
    # Ureias para cálculo de adequação (opcionais — podem vir do laboratório depois)
    ureia_pre: float | None = Field(default=None, gt=0)
    ureia_pos: float | None = Field(default=None, gt=0)


class SessaoOut(BaseModel):
    id: uuid.UUID
    paciente_id: uuid.UUID
    prescricao_hd_id: uuid.UUID | None
    peso_pre_kg: float | None
    pa_pre: str | None
    fc_pre: int | None
    temp_pre: float | None
    queixas: str | None
    inicio: dt.datetime | None
    fim: dt.datetime | None
    maquina: str | None
    peso_pos_kg: float | None
    uf_real_l: float | None
    pa_pos: str | None
    fc_pos: int | None
    ktv: float | None
    urr: float | None
    npcr: float | None
    # Alertas de recepção (ex.: ganho interdialítico excessivo)
    alertas: list[AlertaItem] = []

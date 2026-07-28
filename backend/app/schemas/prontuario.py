"""DTOs do prontuário: paciente, timeline, evolução e exames."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field

# ------------------------------- Paciente -------------------------------
SEGMENTOS_VALIDOS = ("conservador", "hemodialise", "dialise_peritoneal", "transplante")


class PacienteCreate(BaseModel):
    """Cadastro do paciente renal — ambulatório conservador ou TRS."""
    nome: str = Field(min_length=3)
    nome_social: str | None = None
    cns: str | None = Field(default=None, min_length=15, max_length=15)
    cpf: str | None = Field(default=None, min_length=11, max_length=11)
    sexo: str | None = None
    data_nascimento: dt.date | None = None
    etiologia_drc: str | None = None
    estagio_drc: int | None = Field(default=None, ge=1, le=5)
    segmento: str = "conservador"
    inicio_trs: dt.date | None = None    # exigido quando segmento é TRS
    turno_dialise: str | None = None


class PacienteUpdate(BaseModel):
    """Atualização parcial — inclui transição de segmento (ex.: conservador →
    hemodiálise quando o paciente inicia TRS)."""
    nome: str | None = None
    nome_social: str | None = None
    cns: str | None = None
    cpf: str | None = None
    sexo: str | None = None
    data_nascimento: dt.date | None = None
    etiologia_drc: str | None = None
    estagio_drc: int | None = Field(default=None, ge=1, le=5)
    segmento: str | None = None
    inicio_trs: dt.date | None = None
    turno_dialise: str | None = None


class PacienteResumo(BaseModel):
    id: uuid.UUID
    nome: str
    cns: str | None = None
    estagio_drc: int | None = None
    segmento: str | None = None
    turno_dialise: str | None = None


class PacienteHeader(BaseModel):
    id: uuid.UUID
    nome: str
    nome_social: str | None = None
    cns: str | None = None
    cpf: str | None = None
    sexo: str | None = None
    data_nascimento: dt.date | None = None
    idade: int | None = None
    etiologia_drc: str | None = None
    estagio_drc: int | None = None
    segmento: str | None = None
    inicio_trs: dt.date | None = None
    turno_dialise: str | None = None
    alergias: list[str] = []


# ------------------------------- Timeline -------------------------------
class TimelineItem(BaseModel):
    tipo: str  # 'episodio' | 'evolucao' | 'exame'
    subtipo: str | None = None  # ex.: 'sessao_hd', 'medica', código do exame
    titulo: str
    detalhe: str | None = None
    data: dt.datetime
    ref_id: uuid.UUID | None = None


# ------------------------------- Evolução -------------------------------
class EvolucaoCreate(BaseModel):
    categoria: str = "medica"
    subjetivo: str | None = None
    objetivo: str | None = None
    avaliacao: str | None = None
    plano: str | None = None
    texto_livre: str | None = None
    episodio_id: uuid.UUID | None = None
    assinar: bool = False


class EvolucaoOut(BaseModel):
    id: uuid.UUID
    categoria: str
    subjetivo: str | None
    objetivo: str | None
    avaliacao: str | None
    plano: str | None
    texto_livre: str | None
    resumo_ia: str | None
    profissional_id: uuid.UUID
    assinada_em: dt.datetime | None
    created_at: dt.datetime


class ResumoIARequest(BaseModel):
    subjetivo: str | None = None
    objetivo: str | None = None
    avaliacao: str | None = None
    plano: str | None = None
    texto_livre: str | None = None


class ResumoIAResponse(BaseModel):
    resumo: str
    rascunho: bool = True  # sempre rascunho: exige revisão médica antes de assinar


# ------------------------------- Exames / tendência -------------------------------
class PontoExame(BaseModel):
    data: dt.datetime
    valor: float | None
    fora_faixa: bool | None = None


class SerieExame(BaseModel):
    codigo: str
    nome: str
    unidade: str | None
    ref_min: float | None
    ref_max: float | None
    ultimo_valor: float | None
    tendencia: str | None = None  # 'up' | 'down' | 'flat'
    pontos: list[PontoExame] = Field(default_factory=list)

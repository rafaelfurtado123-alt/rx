"""DTOs de gestão: escala de diálise, relatórios/censo/indicadores e faturamento."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field


# ------------------------- Escala de diálise -------------------------
class EscalaCreate(BaseModel):
    turno: str  # 'manha' | 'tarde' | 'noite'
    dias_semana: list[int] = Field(min_length=1)  # ISO 1=segunda .. 7=domingo
    maquina: str | None = None


class EscalaOut(BaseModel):
    id: uuid.UUID
    paciente_id: uuid.UUID
    paciente_nome: str | None = None
    turno: str
    dias_semana: list[int]
    maquina: str | None
    ativo: bool


class EscalaDiaOut(BaseModel):
    data: dt.date
    dia_semana: int
    turnos: dict[str, list[EscalaOut]]  # 'manha'|'tarde'|'noite' → vagas


# ------------------------- Relatórios -------------------------
class CensoOut(BaseModel):
    pacientes_ativos: int
    por_estagio: dict[str, int]
    em_escala_hd: int
    sessoes_30d: int
    intercorrencias_30d: int


class Indicador(BaseModel):
    chave: str
    titulo: str
    valor: float | None  # percentual ou taxa
    unidade: str = "%"
    meta: str | None = None
    status: str | None = None  # 'ok' | 'warn' | 'critical'
    numerador: int = 0
    denominador: int = 0


class IndicadoresOut(BaseModel):
    periodo_dias: int
    indicadores: list[Indicador]


# ------------------------- Faturamento -------------------------
class ProducaoResumo(BaseModel):
    competencia: dt.date
    contas_criadas: int
    contas_existentes: int
    sessoes_faturadas: int


class ContaItemOut(BaseModel):
    sigtap_codigo: str | None
    descricao: str | None
    quantidade: int
    valor: float | None


class ContaOut(BaseModel):
    id: uuid.UUID
    paciente_id: uuid.UUID
    paciente_nome: str | None = None
    paciente_cns: str | None = None
    competencia: dt.date
    tipo: str
    status: str
    itens: list[ContaItemOut] = []


class ApacCreate(BaseModel):
    numero: str | None = None
    competencia: dt.date
    procedimento: str = "0305010107"
    cid: str | None = None
    validade_meses: int = Field(default=3, ge=1, le=12)


class ApacOut(BaseModel):
    id: uuid.UUID
    paciente_id: uuid.UUID
    numero: str | None
    competencia: dt.date
    procedimento: str | None
    cid: str | None
    validade_ini: dt.date | None
    validade_fim: dt.date | None
    status: str

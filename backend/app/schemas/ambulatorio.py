"""DTOs do ambulatório conservador (agenda de consultas + painel)."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel


class ConsultaCreate(BaseModel):
    data_hora: dt.datetime
    tipo: str = "retorno"  # 'primeira_consulta' | 'retorno' | 'preparo_trs'
    profissional_id: uuid.UUID | None = None
    observacao: str | None = None


class ConsultaStatusRequest(BaseModel):
    status: str  # 'realizada' | 'faltou' | 'cancelada'
    observacao: str | None = None


class ConsultaOut(BaseModel):
    id: uuid.UUID
    paciente_id: uuid.UUID
    paciente_nome: str | None = None
    paciente_segmento: str | None = None
    profissional_id: uuid.UUID | None = None
    data_hora: dt.datetime
    tipo: str
    status: str
    observacao: str | None = None
    episodio_id: uuid.UUID | None = None


class PainelAmbulatorio(BaseModel):
    pacientes_conservador: int
    por_estagio: dict[str, int]
    consultas_hoje: int
    consultas_semana: int
    # Estágios 4–5 no conservador: candidatos a preparo para TRS
    candidatos_preparo_trs: int

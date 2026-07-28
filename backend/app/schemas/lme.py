"""DTOs do LME Inteligente."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field


class LmeGerarRequest(BaseModel):
    """Pedido de geração: só o medicamento é obrigatório — o resto é autopreenchido."""
    medicamento_id: uuid.UUID
    posologia: str | None = None
    quantidade_mes: float | None = Field(default=None, gt=0)
    # Overrides opcionais do autopreenchimento
    cid_principal: str | None = None
    anamnese: str | None = None
    justificativa: str | None = None


class ExameChecagem(BaseModel):
    codigo: str
    nome: str
    obrigatorio: bool = True
    situacao: str  # 'presente' | 'ausente' | 'vencido'
    valor: float | None = None
    unidade: str | None = None
    data_coleta: dt.datetime | None = None


class LaudoOut(BaseModel):
    id: uuid.UUID
    status: str
    medicamento: str
    posologia: str | None
    quantidade_mes: float | None
    pcdt_nome: str | None
    pcdt_versao: str | None
    cid_principal: str | None
    cids_secundarios: list[str] = []
    anamnese: str | None
    justificativa: str | None
    exames: list[ExameChecagem] = []
    # Pendências que impedem a emissão (exames ausentes/vencidos, CID fora do PCDT)
    pendencias: list[str] = []
    emitido_em: dt.datetime | None = None
    valido_ate: dt.datetime | None = None
    dias_restantes: int | None = None
    laudo_anterior_id: uuid.UUID | None = None
    termo_versao: str | None = None


class AssinarRequest(BaseModel):
    aceite_termo_por: str | None = None  # paciente/responsável que aceitou o TER

"""DTOs dos dashboards por perfil."""
from __future__ import annotations

from pydantic import BaseModel


class MetricCard(BaseModel):
    chave: str
    titulo: str
    valor: int | float | str
    status: str | None = None  # 'ok' | 'warn' | 'critical' | None


class AlertaProativo(BaseModel):
    nivel: str  # 'warn' | 'critical'
    texto: str
    quantidade: int | None = None


class DashboardResponse(BaseModel):
    perfil: str
    saudacao: str
    metricas: list[MetricCard]
    alertas: list[AlertaProativo]

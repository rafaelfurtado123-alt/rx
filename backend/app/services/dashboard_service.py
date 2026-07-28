"""Montagem dos dashboards por perfil.

As métricas abaixo são calculadas via consultas parametrizadas pela unidade ativa
(o RLS garante o isolamento). Nesta Etapa 3 focamos em contagens de fundação;
as séries clínicas (anemia/DMO/adequação) chegam nas Etapas 4–5.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.core import PacienteUnidade
from ..schemas.auth import CurrentUser
from ..schemas.dashboard import AlertaProativo, DashboardResponse, MetricCard


async def build_dashboard(session: AsyncSession, user: CurrentUser) -> DashboardResponse:
    total_pacientes = await session.scalar(
        select(func.count())
        .select_from(PacienteUnidade)
        .where(
            PacienteUnidade.unidade_id == user.unidade_id,
            PacienteUnidade.ativo.is_(True),
        )
    ) or 0

    perfil = user.papel or "desconhecido"
    metricas, alertas = _por_perfil(perfil, total_pacientes)
    return DashboardResponse(
        perfil=perfil,
        saudacao=_saudacao(user.nome),
        metricas=metricas,
        alertas=alertas,
    )


def _saudacao(nome: str) -> str:
    return f"Olá, {nome}" if nome else "Bem-vindo(a)"


def _por_perfil(
    perfil: str, total_pacientes: int
) -> tuple[list[MetricCard], list[AlertaProativo]]:
    """Cada perfil vê um conjunto próprio de métricas e alertas (placeholders coerentes)."""
    if perfil == "medico":
        return (
            [
                MetricCard(chave="pacientes_hoje", titulo="Pacientes hoje", valor=total_pacientes),
                MetricCard(chave="a_assinar", titulo="A assinar", valor=0, status="warn"),
                MetricCard(chave="lme_vencendo", titulo="LMEs a vencer", valor=0),
                MetricCard(chave="intercorrencias_24h", titulo="Intercorrências 24h", valor=0),
            ],
            [],
        )
    if perfil == "enfermeiro":
        return (
            [
                MetricCard(chave="sala_hd", titulo="Pacientes na sala", valor=total_pacientes),
                MetricCard(chave="emar_pendente", titulo="eMAR pendente", valor=0, status="warn"),
                MetricCard(chave="recepcoes", titulo="Recepções", valor=0),
                MetricCard(chave="sae_assinar", titulo="SAE a assinar", valor=0),
            ],
            [],
        )
    if perfil == "tecnico":
        return (
            [
                MetricCard(chave="sessoes", titulo="Sessões atribuídas", valor=0),
                MetricCard(chave="parametros", titulo="Parâmetros a registrar", valor=0),
                MetricCard(chave="checklist", titulo="Checklist de máquina", valor=0),
            ],
            [],
        )
    if perfil == "equipe_multi":
        return (
            [
                MetricCard(chave="pacientes", titulo="Pacientes da unidade",
                           valor=total_pacientes),
                MetricCard(chave="consultas_hoje", titulo="Consultas hoje", valor=0),
                MetricCard(chave="evolucoes_pendentes",
                           titulo="Evoluções a registrar", valor=0),
                MetricCard(chave="interconsultas", titulo="Interconsultas", valor=0),
            ],
            [],
        )
    if perfil == "administrativo":
        return (
            [
                MetricCard(chave="agenda", titulo="Agendamentos hoje", valor=0),
                MetricCard(chave="faturamento", titulo="Contas abertas", valor=0),
                MetricCard(chave="pendencias", titulo="Pendências documentais", valor=0),
                MetricCard(chave="censo", titulo="Pacientes ativos", valor=total_pacientes),
            ],
            [],
        )
    return ([MetricCard(chave="pacientes", titulo="Pacientes", valor=total_pacientes)], [])

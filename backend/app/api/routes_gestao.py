"""Rotas de gestão: escala de diálise, relatórios/censo/indicadores, faturamento."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_authed_session, get_current_user, require_roles
from ..schemas.auth import CurrentUser
from ..schemas.gestao import (
    ApacCreate,
    ApacOut,
    CensoOut,
    ContaOut,
    EscalaCreate,
    EscalaDiaOut,
    EscalaOut,
    IndicadoresOut,
    ProducaoResumo,
)
from ..services import agenda_service, fatura_service, relatorio_service

router = APIRouter(tags=["gestao"])


def _parse_competencia(competencia: str) -> dt.date:
    """'YYYY-MM' → primeiro dia do mês."""
    try:
        ano, mes = competencia.split("-")
        return dt.date(int(ano), int(mes), 1)
    except (ValueError, AttributeError):
        raise HTTPException(400, "competência inválida — use o formato YYYY-MM")


# ------------------------- Escala de diálise -------------------------


@router.post("/pacientes/{paciente_id}/escala", response_model=EscalaOut,
             status_code=201)
async def criar_escala(
    paciente_id: uuid.UUID,
    body: EscalaCreate,
    user: CurrentUser = Depends(
        require_roles("medico", "enfermeiro", "administrativo", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Vaga recorrente (turno + dias + máquina) com checagem de conflito."""
    return await agenda_service.criar(session, str(paciente_id), body, user)


@router.get("/escala", response_model=list[EscalaOut])
async def listar_escala(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await agenda_service.listar(session, str(user.unidade_id))


@router.get("/escala/dia", response_model=EscalaDiaOut)
async def escala_do_dia(
    data: dt.date | None = None,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """Pacientes esperados na sala no dia (padrão: hoje), por turno."""
    return await agenda_service.escala_do_dia(
        session, str(user.unidade_id), data or dt.date.today())


# ------------------------- Relatórios -------------------------


@router.get("/relatorios/censo", response_model=CensoOut)
async def censo(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await relatorio_service.censo(session, str(user.unidade_id))


@router.get("/relatorios/indicadores", response_model=IndicadoresOut)
async def indicadores(
    periodo_dias: int = 90,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """Indicadores de qualidade da unidade (adequação, anemia, DMO, FAV, segurança)."""
    return await relatorio_service.indicadores(
        session, str(user.unidade_id), periodo_dias)


# ------------------------- Faturamento -------------------------


@router.post("/fatura/producao", response_model=ProducaoResumo)
async def gerar_producao(
    competencia: str,
    user: CurrentUser = Depends(
        require_roles("administrativo", "admin", "medico")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Gera as contas da competência a partir das sessões do mês (idempotente)."""
    return await fatura_service.gerar_producao(
        session, str(user.unidade_id), _parse_competencia(competencia), user)


@router.get("/fatura/contas", response_model=list[ContaOut])
async def listar_contas(
    competencia: str | None = None,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await fatura_service.listar_contas(
        session, str(user.unidade_id),
        _parse_competencia(competencia) if competencia else None)


@router.get("/fatura/contas/export")
async def exportar_contas(
    competencia: str,
    user: CurrentUser = Depends(
        require_roles("administrativo", "admin", "medico")),
    session: AsyncSession = Depends(get_authed_session),
):
    """CSV de conferência da produção da competência."""
    csv = await fatura_service.exportar_csv(
        session, str(user.unidade_id), _parse_competencia(competencia))
    return Response(content=csv, media_type="text/csv", headers={
        "Content-Disposition":
            f'attachment; filename="producao-{competencia}.csv"'})


@router.post("/pacientes/{paciente_id}/apac", response_model=ApacOut,
             status_code=201)
async def criar_apac(
    paciente_id: uuid.UUID,
    body: ApacCreate,
    _: CurrentUser = Depends(require_roles("administrativo", "admin", "medico")),
    session: AsyncSession = Depends(get_authed_session),
):
    return await fatura_service.criar_apac(session, str(paciente_id), body)


@router.get("/pacientes/{paciente_id}/apac", response_model=list[ApacOut])
async def listar_apacs(
    paciente_id: uuid.UUID,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await fatura_service.listar_apacs(session, str(paciente_id))

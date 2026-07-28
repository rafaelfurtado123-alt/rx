"""Relatórios da unidade: censo e indicadores de qualidade (padrão diálise).

Indicadores calculados sobre a janela informada (padrão 90 dias):
  * Adequação: % de sessões com Kt/V ≥ 1.2
  * Anemia: % de pacientes com Hb mais recente na meta (10–12 g/dL)
  * DMO: % de pacientes com fósforo mais recente na meta (3.5–5.5 mg/dL)
  * Acesso: % de pacientes com FAV entre os que têm acesso ativo
  * Segurança: intercorrências por 100 sessões
Alinham-se aos indicadores exigidos pelos relatórios de serviços de diálise
(ANVISA) e às metas dos PCDTs de Anemia e DMO-DRC.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.clinico import ExameResultado, RefExame
from ..models.core import Paciente, PacienteUnidade
from ..models.hd import AcessoVascular, Escala, Intercorrencia, SessaoHD
from ..schemas.gestao import CensoOut, Indicador, IndicadoresOut


async def censo(session: AsyncSession, unidade_id: str) -> CensoOut:
    pacientes = list(await session.scalars(
        select(Paciente)
        .join(PacienteUnidade, PacienteUnidade.paciente_id == Paciente.id)
        .where(PacienteUnidade.unidade_id == unidade_id,
               PacienteUnidade.ativo.is_(True),
               Paciente.deleted_at.is_(None))
    ))
    por_estagio: dict[str, int] = {}
    for p in pacientes:
        chave = f"estagio_{p.estagio_drc}" if p.estagio_drc else "sem_estadiamento"
        por_estagio[chave] = por_estagio.get(chave, 0) + 1

    em_escala = await session.scalar(
        select(func.count(func.distinct(Escala.paciente_id)))
        .where(Escala.unidade_id == unidade_id, Escala.ativo.is_(True))
    ) or 0

    corte = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
    sessoes_30d = await session.scalar(
        select(func.count()).select_from(SessaoHD)
        .where(SessaoHD.unidade_id == unidade_id, SessaoHD.inicio >= corte)
    ) or 0
    intercorrencias_30d = await session.scalar(
        select(func.count()).select_from(Intercorrencia)
        .join(SessaoHD, SessaoHD.id == Intercorrencia.sessao_id)
        .where(SessaoHD.unidade_id == unidade_id, Intercorrencia.ts >= corte)
    ) or 0

    return CensoOut(
        pacientes_ativos=len(pacientes), por_estagio=por_estagio,
        em_escala_hd=em_escala, sessoes_30d=sessoes_30d,
        intercorrencias_30d=intercorrencias_30d,
    )


async def _ultimo_exame_por_paciente(
    session: AsyncSession, unidade_id: str, codigo: str
) -> list[float]:
    """Valor mais recente do exame `codigo` para cada paciente ativo da unidade."""
    ref = await session.scalar(select(RefExame).where(RefExame.codigo == codigo))
    if ref is None:
        return []
    sub = (
        select(ExameResultado.paciente_id,
               func.max(ExameResultado.data_coleta).label("ultima"))
        .join(PacienteUnidade,
              PacienteUnidade.paciente_id == ExameResultado.paciente_id)
        .where(PacienteUnidade.unidade_id == unidade_id,
               ExameResultado.exame_id == ref.id,
               ExameResultado.valor.is_not(None))
        .group_by(ExameResultado.paciente_id)
        .subquery()
    )
    rows = await session.execute(
        select(ExameResultado.valor)
        .join(sub, (sub.c.paciente_id == ExameResultado.paciente_id)
              & (sub.c.ultima == ExameResultado.data_coleta))
        .where(ExameResultado.exame_id == ref.id)
    )
    return [float(v[0]) for v in rows]


def _pct(numerador: int, denominador: int) -> float | None:
    if denominador == 0:
        return None
    return round(numerador / denominador * 100, 1)


def _indicador_meta(chave: str, titulo: str, meta: str, num: int, den: int,
                    alvo_pct: float) -> Indicador:
    valor = _pct(num, den)
    status = None
    if valor is not None:
        status = "ok" if valor >= alvo_pct else (
            "warn" if valor >= alvo_pct - 20 else "critical")
    return Indicador(chave=chave, titulo=titulo, valor=valor, meta=meta,
                     status=status, numerador=num, denominador=den)


async def indicadores(
    session: AsyncSession, unidade_id: str, periodo_dias: int = 90
) -> IndicadoresOut:
    corte = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=periodo_dias)
    saida: list[Indicador] = []

    # Adequação — % sessões com Kt/V ≥ 1.2 no período
    sessoes_ktv = [
        float(k[0]) for k in await session.execute(
            select(SessaoHD.ktv).where(
                SessaoHD.unidade_id == unidade_id,
                SessaoHD.inicio >= corte, SessaoHD.ktv.is_not(None)))
    ]
    saida.append(_indicador_meta(
        "ktv_adequado", "Sessões com Kt/V ≥ 1.2", "≥ 85% das sessões",
        sum(1 for k in sessoes_ktv if k >= 1.2), len(sessoes_ktv), 85))

    # Anemia — % pacientes com Hb mais recente entre 10 e 12
    hbs = await _ultimo_exame_por_paciente(session, unidade_id, "HB")
    saida.append(_indicador_meta(
        "hb_na_meta", "Pacientes com Hb 10–12 g/dL", "≥ 70% dos pacientes",
        sum(1 for v in hbs if 10 <= v <= 12), len(hbs), 70))

    # DMO — % pacientes com fósforo mais recente entre 3.5 e 5.5
    fosforos = await _ultimo_exame_por_paciente(session, unidade_id, "P")
    saida.append(_indicador_meta(
        "p_na_meta", "Pacientes com fósforo 3.5–5.5 mg/dL", "≥ 70% dos pacientes",
        sum(1 for v in fosforos if 3.5 <= v <= 5.5), len(fosforos), 70))

    # Acesso — % com FAV entre pacientes com acesso ativo na unidade
    acessos = await session.execute(
        select(AcessoVascular.paciente_id, AcessoVascular.tipo)
        .join(PacienteUnidade,
              PacienteUnidade.paciente_id == AcessoVascular.paciente_id)
        .where(PacienteUnidade.unidade_id == unidade_id,
               AcessoVascular.status == "ativo")
    )
    por_paciente: dict[str, set[str]] = {}
    for pid, tipo in acessos:
        por_paciente.setdefault(str(pid), set()).add(tipo)
    com_fav = sum(1 for tipos in por_paciente.values() if "fav" in tipos)
    saida.append(_indicador_meta(
        "fav_pct", "Pacientes com FAV", "≥ 60% dos pacientes com acesso",
        com_fav, len(por_paciente), 60))

    # Segurança — intercorrências por 100 sessões (menor é melhor)
    total_sessoes = await session.scalar(
        select(func.count()).select_from(SessaoHD)
        .where(SessaoHD.unidade_id == unidade_id, SessaoHD.inicio >= corte)) or 0
    total_interc = await session.scalar(
        select(func.count()).select_from(Intercorrencia)
        .join(SessaoHD, SessaoHD.id == Intercorrencia.sessao_id)
        .where(SessaoHD.unidade_id == unidade_id,
               Intercorrencia.ts >= corte)) or 0
    taxa = round(total_interc / total_sessoes * 100, 1) if total_sessoes else None
    saida.append(Indicador(
        chave="intercorrencias_100_sessoes",
        titulo="Intercorrências por 100 sessões", valor=taxa, unidade="/100",
        meta="quanto menor, melhor",
        status=None if taxa is None else (
            "ok" if taxa <= 10 else ("warn" if taxa <= 25 else "critical")),
        numerador=total_interc, denominador=total_sessoes))

    return IndicadoresOut(periodo_dias=periodo_dias, indicadores=saida)

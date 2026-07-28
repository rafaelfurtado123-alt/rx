"""Faturamento SUS: produção mensal (contas por competência) e APAC de TRS.

A produção do mês agrupa as sessões de HD encerradas na competência por
paciente e gera uma conta com o procedimento SIGTAP de hemodiálise. A geração
é idempotente: pacientes que já têm conta na competência são pulados. O export
CSV serve como arquivo de conferência (o layout magnético BPA/APAC entra na
fase de integração com o gestor).
"""
from __future__ import annotations

import calendar
import datetime as dt
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.core import Paciente
from ..models.fatura import Apac, Conta, ContaItem, RefSigtap
from ..models.hd import SessaoHD
from ..schemas.auth import CurrentUser
from ..schemas.gestao import (
    ApacCreate,
    ApacOut,
    ContaItemOut,
    ContaOut,
    ProducaoResumo,
)

PROCEDIMENTO_HD = "0305010107"  # Hemodiálise (máx. 3 sessões/semana)


def _janela_competencia(competencia: dt.date) -> tuple[dt.datetime, dt.datetime]:
    ini = dt.datetime(competencia.year, competencia.month, 1, tzinfo=dt.timezone.utc)
    ultimo_dia = calendar.monthrange(competencia.year, competencia.month)[1]
    fim = ini + dt.timedelta(days=ultimo_dia)
    return ini, fim


async def gerar_producao(
    session: AsyncSession, unidade_id: str, competencia: dt.date, user: CurrentUser
) -> ProducaoResumo:
    """Gera as contas da competência a partir das sessões encerradas no mês."""
    competencia = competencia.replace(day=1)
    ini, fim = _janela_competencia(competencia)

    # Sessões encerradas no mês, agrupadas por paciente
    rows = await session.execute(
        select(SessaoHD.paciente_id, func.count())
        .where(SessaoHD.unidade_id == unidade_id,
               SessaoHD.fim.is_not(None),
               SessaoHD.fim >= ini, SessaoHD.fim < fim)
        .group_by(SessaoHD.paciente_id)
    )
    sessoes_por_paciente = {str(pid): int(qtd) for pid, qtd in rows}

    sigtap = await session.get(RefSigtap, PROCEDIMENTO_HD)
    valor_unit = float(sigtap.valor_sus) if sigtap and sigtap.valor_sus else None

    criadas = existentes = sessoes_faturadas = 0
    for paciente_id, qtd in sessoes_por_paciente.items():
        ja_existe = await session.scalar(
            select(Conta).where(Conta.paciente_id == paciente_id,
                                Conta.unidade_id == unidade_id,
                                Conta.competencia == competencia)
        )
        if ja_existe is not None:
            existentes += 1
            continue
        conta = Conta(paciente_id=paciente_id, unidade_id=unidade_id,
                      competencia=competencia)
        session.add(conta)
        await session.flush()
        session.add(ContaItem(
            conta_id=conta.id, sigtap_codigo=PROCEDIMENTO_HD, quantidade=qtd,
            valor=valor_unit * qtd if valor_unit is not None else None))
        criadas += 1
        sessoes_faturadas += qtd

    await session.commit()
    return ProducaoResumo(competencia=competencia, contas_criadas=criadas,
                          contas_existentes=existentes,
                          sessoes_faturadas=sessoes_faturadas)


async def listar_contas(
    session: AsyncSession, unidade_id: str, competencia: dt.date | None = None
) -> list[ContaOut]:
    stmt = select(Conta).where(Conta.unidade_id == unidade_id)
    if competencia is not None:
        stmt = stmt.where(Conta.competencia == competencia.replace(day=1))
    stmt = stmt.order_by(Conta.competencia.desc())
    contas = await session.scalars(stmt)

    out: list[ContaOut] = []
    for conta in contas:
        paciente = await session.get(Paciente, conta.paciente_id)
        itens = await session.scalars(
            select(ContaItem).where(ContaItem.conta_id == conta.id))
        itens_out: list[ContaItemOut] = []
        for item in itens:
            sigtap = (await session.get(RefSigtap, item.sigtap_codigo)
                      if item.sigtap_codigo else None)
            itens_out.append(ContaItemOut(
                sigtap_codigo=item.sigtap_codigo,
                descricao=sigtap.descricao if sigtap else None,
                quantidade=item.quantidade,
                valor=float(item.valor) if item.valor is not None else None))
        out.append(ContaOut(
            id=conta.id, paciente_id=conta.paciente_id,
            paciente_nome=paciente.nome if paciente else None,
            paciente_cns=paciente.cns if paciente else None,
            competencia=conta.competencia, tipo=conta.tipo, status=conta.status,
            itens=itens_out))
    return out


async def exportar_csv(
    session: AsyncSession, unidade_id: str, competencia: dt.date
) -> str:
    """CSV de conferência da produção da competência."""
    contas = await listar_contas(session, unidade_id, competencia)
    linhas = ["competencia;paciente;cns;procedimento;descricao;quantidade;valor"]
    for conta in contas:
        for item in conta.itens:
            linhas.append(";".join([
                conta.competencia.strftime("%Y-%m"),
                conta.paciente_nome or "",
                conta.paciente_cns or "",
                item.sigtap_codigo or "",
                item.descricao or "",
                str(item.quantidade),
                f"{item.valor:.2f}" if item.valor is not None else "",
            ]))
    return "\n".join(linhas) + "\n"


# ------------------------- APAC -------------------------
async def criar_apac(
    session: AsyncSession, paciente_id: str, body: ApacCreate
) -> ApacOut:
    competencia = body.competencia.replace(day=1)
    ini = competencia
    # validade em competências (meses)
    mes = competencia.month - 1 + body.validade_meses
    fim = dt.date(competencia.year + mes // 12, mes % 12 + 1, 1) - dt.timedelta(days=1)

    numero = body.numero or f"APAC{competencia.strftime('%y%m')}{uuid.uuid4().hex[:8].upper()}"
    apac = Apac(paciente_id=paciente_id, numero=numero, competencia=competencia,
                procedimento=body.procedimento, cid=body.cid,
                validade_ini=ini, validade_fim=fim)
    session.add(apac)
    await session.commit()
    return _apac_out(apac)


async def listar_apacs(session: AsyncSession, paciente_id: str) -> list[ApacOut]:
    rows = await session.scalars(
        select(Apac).where(Apac.paciente_id == paciente_id)
        .order_by(Apac.competencia.desc()))
    hoje = dt.date.today()
    out = []
    for a in rows:
        if a.status == "ativa" and a.validade_fim and a.validade_fim < hoje:
            a.status = "vencida"
    await session.commit()
    for a in await session.scalars(
            select(Apac).where(Apac.paciente_id == paciente_id)
            .order_by(Apac.competencia.desc())):
        out.append(_apac_out(a))
    return out


def _apac_out(a: Apac) -> ApacOut:
    return ApacOut(id=a.id, paciente_id=a.paciente_id, numero=a.numero,
                   competencia=a.competencia, procedimento=a.procedimento,
                   cid=a.cid, validade_ini=a.validade_ini,
                   validade_fim=a.validade_fim, status=a.status)

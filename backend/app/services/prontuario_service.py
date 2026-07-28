"""Regras do prontuário: header do paciente, timeline unificada e séries de exames."""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.clinico import Alergia, Episodio, Evolucao, ExameResultado, RefExame
from ..models.core import SEGMENTOS, Paciente, PacienteUnidade
from ..schemas.auth import CurrentUser
from ..schemas.prontuario import (
    PacienteCreate,
    PacienteHeader,
    PacienteResumo,
    PacienteUpdate,
    PontoExame,
    SerieExame,
    TimelineItem,
)

_EP_TITULO = {
    "consulta": "Consulta",
    "sessao_hd": "Sessão de HD",
    "internacao": "Internação",
    "intercorrencia": "Intercorrência",
    "telemedicina": "Teleconsulta",
    "procedimento": "Procedimento",
}
_CAT_TITULO = {
    "medica": "Evolução médica",
    "enfermagem": "Evolução de enfermagem",
    "nutricao": "Evolução de nutrição",
    "servico_social": "Evolução de serviço social",
    "psicologia": "Evolução de psicologia",
    "farmacia": "Evolução de farmácia",
    "fisioterapia": "Evolução de fisioterapia",
}


def _idade(nasc: dt.date | None) -> int | None:
    if nasc is None:
        return None
    hoje = dt.date.today()
    return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))


async def listar_pacientes(
    session: AsyncSession, unidade_id: str, segmento: str | None = None
) -> list[PacienteResumo]:
    """Pacientes ativos (RLS já filtra pela unidade), opcionalmente por segmento."""
    stmt = select(Paciente).where(Paciente.deleted_at.is_(None))
    if segmento is not None:
        if segmento not in SEGMENTOS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "segmento inválido")
        stmt = stmt.where(Paciente.segmento == segmento)
    rows = await session.scalars(stmt.order_by(Paciente.nome))
    return [
        PacienteResumo(
            id=p.id, nome=p.nome, cns=p.cns, estagio_drc=p.estagio_drc,
            segmento=p.segmento, turno_dialise=p.turno_dialise,
        )
        for p in rows
    ]


def _validar_segmento_trs(segmento: str, inicio_trs, turno) -> None:
    if segmento not in SEGMENTOS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"segmento inválido (use: {', '.join(SEGMENTOS)})")
    if segmento == "hemodialise" and inicio_trs is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "informe inicio_trs para paciente em hemodiálise")


async def criar_paciente(
    session: AsyncSession, body: PacienteCreate, user: CurrentUser
) -> PacienteHeader:
    """Cadastro do paciente renal, vinculado à unidade ativa do profissional."""
    _validar_segmento_trs(body.segmento, body.inicio_trs, body.turno_dialise)

    paciente = Paciente(
        nome=body.nome, nome_social=body.nome_social, cns=body.cns, cpf=body.cpf,
        sexo=body.sexo or "nao_informado", data_nascimento=body.data_nascimento,
        etiologia_drc=body.etiologia_drc, estagio_drc=body.estagio_drc,
        segmento=body.segmento, inicio_trs=body.inicio_trs,
        turno_dialise=body.turno_dialise,
    )
    session.add(paciente)
    await session.flush()
    session.add(PacienteUnidade(paciente_id=paciente.id,
                                unidade_id=user.unidade_id))
    await session.commit()
    return await get_header(session, str(paciente.id))


async def atualizar_paciente(
    session: AsyncSession, paciente_id: str, body: PacienteUpdate
) -> PacienteHeader:
    """Atualização parcial do cadastro (inclui transição de segmento)."""
    paciente = await session.get(Paciente, paciente_id)
    if paciente is None or paciente.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "paciente não encontrado")

    campos = body.model_dump(exclude_unset=True)
    if "segmento" in campos:
        inicio = campos.get("inicio_trs", paciente.inicio_trs)
        turno = campos.get("turno_dialise", paciente.turno_dialise)
        _validar_segmento_trs(campos["segmento"], inicio, turno)
    for campo, valor in campos.items():
        setattr(paciente, campo, valor)
    await session.commit()
    return await get_header(session, paciente_id)


async def get_header(session: AsyncSession, paciente_id: str) -> PacienteHeader:
    p = await session.get(Paciente, paciente_id)
    if p is None or p.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "paciente não encontrado")
    alergias = await session.scalars(
        select(Alergia.substancia).where(
            Alergia.paciente_id == paciente_id, Alergia.ativo.is_(True)
        )
    )
    return PacienteHeader(
        id=p.id, nome=p.nome, nome_social=p.nome_social, cns=p.cns, cpf=p.cpf,
        sexo=p.sexo, data_nascimento=p.data_nascimento, idade=_idade(p.data_nascimento),
        etiologia_drc=p.etiologia_drc, estagio_drc=p.estagio_drc,
        segmento=p.segmento, inicio_trs=p.inicio_trs, turno_dialise=p.turno_dialise,
        alergias=list(alergias),
    )


async def timeline(session: AsyncSession, paciente_id: str, limite: int = 50) -> list[TimelineItem]:
    """Linha do tempo unificada: episódios + evoluções + exames, ordenados por data desc."""
    itens: list[TimelineItem] = []

    episodios = await session.scalars(
        select(Episodio).where(Episodio.paciente_id == paciente_id)
        .order_by(Episodio.inicio.desc()).limit(limite)
    )
    for e in episodios:
        itens.append(TimelineItem(
            tipo="episodio", subtipo=e.tipo,
            titulo=_EP_TITULO.get(e.tipo, e.tipo), detalhe=e.resumo,
            data=e.inicio, ref_id=e.id,
        ))

    evolucoes = await session.scalars(
        select(Evolucao).where(
            Evolucao.paciente_id == paciente_id, Evolucao.deleted_at.is_(None)
        ).order_by(Evolucao.created_at.desc()).limit(limite)
    )
    for ev in evolucoes:
        resumo = ev.avaliacao or ev.plano or ev.texto_livre or ev.resumo_ia
        itens.append(TimelineItem(
            tipo="evolucao", subtipo=ev.categoria,
            titulo=_CAT_TITULO.get(ev.categoria, "Evolução"),
            detalhe=(resumo[:120] if resumo else None),
            data=ev.created_at, ref_id=ev.id,
        ))

    exames = await session.execute(
        select(ExameResultado, RefExame)
        .join(RefExame, RefExame.id == ExameResultado.exame_id)
        .where(ExameResultado.paciente_id == paciente_id)
        .order_by(ExameResultado.data_coleta.desc()).limit(limite)
    )
    for res, ref in exames:
        # :g normaliza o Decimal vindo do banco (evita “9.4000…0355” de floats)
        valor = f"{float(res.valor):g}" if res.valor is not None \
            else (res.valor_texto or "-")
        flag = " (fora da faixa)" if res.fora_faixa else ""
        itens.append(TimelineItem(
            tipo="exame", subtipo=ref.codigo,
            titulo=ref.nome, detalhe=f"{valor} {res.unidade or ref.unidade or ''}{flag}".strip(),
            data=res.data_coleta, ref_id=res.id,
        ))

    itens.sort(key=lambda i: i.data, reverse=True)
    return itens[:limite]


async def serie_exame(session: AsyncSession, paciente_id: str, codigo: str) -> SerieExame:
    """Série temporal de um exame para o gráfico de tendência."""
    ref = await session.scalar(select(RefExame).where(RefExame.codigo == codigo))
    if ref is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "exame não catalogado")

    resultados = list(await session.scalars(
        select(ExameResultado).where(
            ExameResultado.paciente_id == paciente_id,
            ExameResultado.exame_id == ref.id,
        ).order_by(ExameResultado.data_coleta.asc())
    ))
    pontos = [
        PontoExame(data=r.data_coleta, valor=float(r.valor) if r.valor is not None else None,
                   fora_faixa=r.fora_faixa)
        for r in resultados
    ]
    valores = [p.valor for p in pontos if p.valor is not None]
    tendencia = None
    if len(valores) >= 2:
        delta = valores[-1] - valores[-2]
        tendencia = "up" if delta > 0 else ("down" if delta < 0 else "flat")

    return SerieExame(
        codigo=ref.codigo or codigo, nome=ref.nome, unidade=ref.unidade,
        ref_min=float(ref.ref_min) if ref.ref_min is not None else None,
        ref_max=float(ref.ref_max) if ref.ref_max is not None else None,
        ultimo_valor=valores[-1] if valores else None,
        tendencia=tendencia, pontos=pontos,
    )

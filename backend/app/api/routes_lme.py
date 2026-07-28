"""Rotas do LME Inteligente: gerar, assinar, renovar, histórico, PDFs."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_authed_session, get_current_user, require_roles
from ..models.core import Paciente, Profissional, Unidade
from ..models.lme import Termo
from ..schemas.auth import CurrentUser
from ..schemas.lme import AssinarRequest, LaudoOut, LmeGerarRequest
from ..services import lme_service, pdf_service

router = APIRouter(tags=["lme"])


@router.get("/medicamentos")
async def listar_medicamentos(
    ceaf: bool | None = None,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """Catálogo de medicamentos (filtro `ceaf=true` para os que exigem LME)."""
    from ..models.hd import RefMedicamento

    stmt = select(RefMedicamento).where(RefMedicamento.ativo.is_(True))
    if ceaf is not None:
        stmt = stmt.where(RefMedicamento.ceaf.is_(ceaf))
    rows = await session.scalars(stmt.order_by(RefMedicamento.principio_ativo))
    return [
        {"id": str(m.id), "principio_ativo": m.principio_ativo,
         "apresentacao": m.apresentacao, "requer_lme": m.requer_lme}
        for m in rows
    ]


@router.post("/pacientes/{paciente_id}/lme", response_model=LaudoOut, status_code=201)
async def gerar_lme(
    paciente_id: uuid.UUID,
    body: LmeGerarRequest,
    # Emitir LME é ato médico
    user: CurrentUser = Depends(require_roles("medico", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Gera o LME com autopreenchimento PCDT (rascunho; lista pendências)."""
    return await lme_service.gerar(session, str(paciente_id), body, user)


@router.get("/pacientes/{paciente_id}/lme", response_model=list[LaudoOut])
async def listar_lmes(
    paciente_id: uuid.UUID,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """Histórico de LMEs (vencimento marcado automaticamente na leitura)."""
    return await lme_service.listar(session, str(paciente_id))


@router.get("/lme/{laudo_id}", response_model=LaudoOut)
async def obter_lme(
    laudo_id: uuid.UUID,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    return await lme_service.obter(session, str(laudo_id))


@router.post("/lme/{laudo_id}/assinar", response_model=LaudoOut)
async def assinar_lme(
    laudo_id: uuid.UUID,
    body: AssinarRequest,
    user: CurrentUser = Depends(require_roles("medico", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Assina/emite (bloqueado se houver pendência). Validade: 90 dias."""
    return await lme_service.assinar(session, str(laudo_id),
                                     body.aceite_termo_por, user)


@router.post("/lme/{laudo_id}/renovar", response_model=LaudoOut, status_code=201)
async def renovar_lme(
    laudo_id: uuid.UUID,
    user: CurrentUser = Depends(require_roles("medico", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Renovação em 1 clique (clona, reavalia exames, encadeia a origem)."""
    return await lme_service.renovar(session, str(laudo_id), user)


@router.get("/lme/{laudo_id}/pdf")
async def pdf_lme(
    laudo_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """PDF oficial do LME (gerado on-demand)."""
    laudo = await lme_service.obter(session, str(laudo_id))
    row = await lme_service._get_laudo(session, str(laudo_id))
    paciente = await session.get(Paciente, row.paciente_id)
    medico = await session.get(Profissional, row.medico_id)
    unidade = await session.get(Unidade, row.unidade_id)
    pdf = pdf_service.gerar_pdf_lme(laudo, paciente, medico, unidade)
    return Response(content=pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="lme-{laudo_id}.pdf"'})


@router.get("/lme/{laudo_id}/termo/pdf")
async def pdf_termo(
    laudo_id: uuid.UUID,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """PDF do Termo de Esclarecimento e Responsabilidade."""
    laudo = await lme_service.obter(session, str(laudo_id))
    row = await lme_service._get_laudo(session, str(laudo_id))
    paciente = await session.get(Paciente, row.paciente_id)
    termo = await session.scalar(select(Termo).where(Termo.laudo_id == row.id))
    texto = termo.texto if termo else ""
    pdf = pdf_service.gerar_pdf_termo(
        texto, paciente, laudo.medicamento,
        termo.aceite_por if termo else None,
        termo.aceite_em if termo else None)
    return Response(content=pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="ter-{laudo_id}.pdf"'})

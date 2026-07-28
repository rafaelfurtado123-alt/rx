"""Rotas de assinatura digital ICP-Brasil em nuvem (VIDaaS / CRM Digital)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..core.deps import get_authed_session, get_current_user, require_roles
from ..schemas.auth import CurrentUser
from ..services import assinatura_service

router = APIRouter(prefix="/assinatura", tags=["assinatura"])


@router.post("/vidaas/autorizacao", status_code=201)
async def iniciar_autorizacao(
    user: CurrentUser = Depends(require_roles("medico", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Inicia a sessão OAuth2/PKCE — devolve a URL para aprovar no app VIDaaS."""
    return await assinatura_service.iniciar_autorizacao(session, user)


@router.get("/vidaas/callback", response_class=HTMLResponse)
async def callback(
    state: str,
    code: str,
    session: AsyncSession = Depends(get_session),
):
    """Redirect do PSC após a aprovação no app (público; validado pelo state)."""
    await assinatura_service.concluir_autorizacao(session, state, code)
    return HTMLResponse(
        "<html><body style='font-family:sans-serif;text-align:center;"
        "padding-top:20vh'><h2>Autorização concluída ✓</h2>"
        "<p>Volte ao Néfron para assinar o documento.</p></body></html>"
    )


@router.get("/vidaas/autorizacao/{state}")
async def status_autorizacao(
    state: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """Polling do app: pendente | autorizada | expirada | erro."""
    return await assinatura_service.status_autorizacao(session, state, user)


@router.post("/vidaas/lme/{laudo_id}", status_code=201)
async def assinar_lme_icp(
    laudo_id: uuid.UUID,
    user: CurrentUser = Depends(require_roles("medico", "admin")),
    session: AsyncSession = Depends(get_authed_session),
):
    """Assina o PDF do LME com o certificado em nuvem (hash SHA-256 → CMS)."""
    return await assinatura_service.assinar_lme(session, str(laudo_id), user)


@router.get("/{assinatura_id}/p7s")
async def baixar_p7s(
    assinatura_id: uuid.UUID,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """Assinatura destacada (.p7s) — verificável no validador ITI com o PDF."""
    conteudo = await assinatura_service.baixar_p7s(session, str(assinatura_id))
    return Response(content=conteudo, media_type="application/pkcs7-signature",
                    headers={"Content-Disposition":
                             f'attachment; filename="{assinatura_id}.p7s"'})


@router.get("/{assinatura_id}/documento")
async def baixar_documento(
    assinatura_id: uuid.UUID,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """Cópia exata do PDF assinado (par do .p7s na verificação)."""
    conteudo = await assinatura_service.baixar_documento(
        session, str(assinatura_id))
    return Response(content=conteudo, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'inline; filename="{assinatura_id}-assinado.pdf"'})

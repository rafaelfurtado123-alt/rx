"""Assinatura digital ICP-Brasil em nuvem via VIDaaS (Valid / CRM Digital).

Fluxo (padrão API PSC ICP-Brasil — OAuth2 authorization_code + PKCE):
  1. `iniciar_autorizacao` — gera state + code_verifier/challenge e devolve a
     URL de autorização. O médico aprova no app VIDaaS (push/QR, com o
     certificado obtido pelo CRM Digital).
  2. O PSC redireciona para o callback com `code`; `concluir_autorizacao`
     troca o code por um access_token de sessão de assinatura (vida curta).
  3. `assinar_lme` — gera o PDF oficial, calcula SHA-256 e envia o hash ao
     endpoint de assinatura do PSC; recebe a assinatura CMS/PKCS#7 destacada
     (base64), grava em `seguranca.assinatura` e vincula ao laudo.

Provedores:
  * `VidaasProvider` — HTTP real (httpx), endpoints configuráveis por env.
  * `MockVidaasProvider` — determinístico, sem rede; usado quando
    NEFRON_VIDAAS_MOCK=true ou sem client_id (dev/teste/homologação).

Evolução prevista: embutir a assinatura no PDF (PAdES, via pyHanko) — hoje o
par (PDF + .p7s destacado) já é verificável no validador ITI.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import secrets
from typing import Protocol
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..models.core import Paciente, Profissional, Unidade
from ..models.lme import Laudo
from ..models.seguranca import Assinatura, VidaasSessao
from ..schemas.auth import CurrentUser
from . import lme_service, pdf_service

SHA256_OID = "2.16.840.1.101.3.4.2.1"


# ------------------------- Provedores -------------------------
class AssinaturaProvider(Protocol):
    def authorization_url(self, state: str, code_challenge: str,
                          cpf: str | None) -> str: ...

    async def trocar_code_por_token(self, code: str, code_verifier: str) -> dict: ...

    async def assinar_hash(self, access_token: str, doc_id: str, alias: str,
                           hash_b64: str) -> dict: ...


class VidaasProvider:
    """Cliente HTTP da API PSC do VIDaaS (endpoints configuráveis)."""

    def __init__(self) -> None:
        self.s = get_settings()

    def authorization_url(self, state: str, code_challenge: str,
                          cpf: str | None) -> str:
        params = {
            "client_id": self.s.vidaas_client_id,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "response_type": "code",
            "scope": "signature_session",
            "redirect_uri": self.s.vidaas_redirect_uri,
            "state": state,
        }
        if cpf:
            params["login_hint"] = cpf  # dispara push no app do titular
        return f"{self.s.vidaas_base_url}/v0/oauth/authorize?{urlencode(params)}"

    async def trocar_code_por_token(self, code: str, code_verifier: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.s.vidaas_base_url}/v0/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.s.vidaas_client_id,
                    "client_secret": self.s.vidaas_client_secret,
                    "code": code,
                    "redirect_uri": self.s.vidaas_redirect_uri,
                    "code_verifier": code_verifier,
                },
            )
        if r.status_code != 200:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                                f"PSC recusou o code: {r.text[:200]}")
        return r.json()

    async def assinar_hash(self, access_token: str, doc_id: str, alias: str,
                           hash_b64: str) -> dict:
        payload = {"hashes": [{
            "id": doc_id,
            "alias": alias,
            "hash": hash_b64,
            "hash_algorithm": SHA256_OID,
            "signature_format": "CMS",
        }]}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self.s.vidaas_base_url}/valid/api/v1/trusted-services/signatures",
                headers={"Authorization": f"Bearer {access_token}"},
                json=payload,
            )
        if r.status_code != 200:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                                f"PSC recusou a assinatura: {r.text[:200]}")
        data = r.json()
        assinaturas = data.get("signatures") or data.get("hashes") or []
        if not assinaturas:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                                "PSC não devolveu assinatura")
        primeira = assinaturas[0]
        return {
            "assinatura_b64": primeira.get("raw_signature")
            or primeira.get("signature"),
            "certificado": {"origem": "vidaas",
                            "alias": primeira.get("alias", alias)},
        }


class MockVidaasProvider:
    """Simulação determinística do PSC — sem rede, para dev/teste/homologação."""

    def authorization_url(self, state: str, code_challenge: str,
                          cpf: str | None) -> str:
        return (f"https://vidaas.mock/authorize?state={state}"
                f"&code_challenge={code_challenge}")

    async def trocar_code_por_token(self, code: str, code_verifier: str) -> dict:
        # Aceita qualquer code não-vazio; token derivado determinístico.
        if not code:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "code vazio")
        token = hashlib.sha256(f"{code}:{code_verifier}".encode()).hexdigest()
        return {"access_token": f"mock-{token[:32]}", "expires_in": 1800}

    async def assinar_hash(self, access_token: str, doc_id: str, alias: str,
                           hash_b64: str) -> dict:
        if not access_token.startswith("mock-"):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token inválido")
        fake = hashlib.sha256(f"{access_token}:{hash_b64}".encode()).digest()
        return {
            "assinatura_b64": base64.b64encode(b"MOCK-CMS:" + fake).decode(),
            "certificado": {"origem": "vidaas-mock", "cn": alias,
                            "icp_brasil": False,
                            "aviso": "assinatura simulada — não válida"},
        }


def get_provider() -> AssinaturaProvider:
    s = get_settings()
    if s.vidaas_mock or not s.vidaas_client_id:
        return MockVidaasProvider()
    return VidaasProvider()


# ------------------------- Casos de uso -------------------------
def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


async def iniciar_autorizacao(
    session: AsyncSession, user: CurrentUser
) -> dict:
    prof = await session.get(Profissional, user.profissional_id)
    verifier, challenge = _pkce()
    state = secrets.token_urlsafe(24)
    sessao = VidaasSessao(profissional_id=user.profissional_id, state=state,
                          code_verifier=verifier)
    session.add(sessao)
    await session.commit()
    url = get_provider().authorization_url(
        state, challenge, prof.cpf if prof else None)
    return {"state": state, "authorization_url": url,
            "mock": isinstance(get_provider(), MockVidaasProvider)}


async def concluir_autorizacao(
    session: AsyncSession, state: str, code: str
) -> dict:
    """Chamado pelo callback do PSC (redirect do navegador) — valida por state."""
    sessao = await session.scalar(
        select(VidaasSessao).where(VidaasSessao.state == state))
    if sessao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "state desconhecido")
    if sessao.status != "pendente":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"sessão em status '{sessao.status}'")
    try:
        token = await get_provider().trocar_code_por_token(
            code, sessao.code_verifier)
    except HTTPException:
        sessao.status = "erro"
        await session.commit()
        raise
    settings = get_settings()
    ttl = int(token.get("expires_in")
              or settings.vidaas_token_ttl_min * 60)
    sessao.access_token = token["access_token"]
    sessao.token_expira_em = (dt.datetime.now(dt.timezone.utc)
                              + dt.timedelta(seconds=ttl))
    sessao.status = "autorizada"
    await session.commit()
    return {"status": "autorizada"}


async def status_autorizacao(
    session: AsyncSession, state: str, user: CurrentUser
) -> dict:
    sessao = await session.scalar(
        select(VidaasSessao).where(VidaasSessao.state == state))
    if sessao is None or str(sessao.profissional_id) != str(user.profissional_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "sessão não encontrada")
    if (sessao.status == "autorizada" and sessao.token_expira_em is not None
            and sessao.token_expira_em < dt.datetime.now(dt.timezone.utc)):
        sessao.status = "expirada"
        await session.commit()
    return {"state": state, "status": sessao.status}


async def _sessao_autorizada(
    session: AsyncSession, user: CurrentUser
) -> VidaasSessao:
    sessao = await session.scalar(
        select(VidaasSessao)
        .where(VidaasSessao.profissional_id == user.profissional_id,
               VidaasSessao.status == "autorizada")
        .order_by(VidaasSessao.created_at.desc()).limit(1))
    agora = dt.datetime.now(dt.timezone.utc)
    if sessao is None or (sessao.token_expira_em is not None
                          and sessao.token_expira_em < agora):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "nenhuma sessão VIDaaS autorizada — autorize no app antes de assinar")
    return sessao


async def assinar_lme(
    session: AsyncSession, laudo_id: str, user: CurrentUser
) -> dict:
    """Assina digitalmente o PDF do LME com o certificado em nuvem do médico."""
    laudo_row = await session.get(Laudo, laudo_id)
    if laudo_row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "laudo não encontrado")
    if laudo_row.status not in ("vigente", "assinado", "emitido"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "emita o LME (assinatura eletrônica) antes da assinatura ICP-Brasil")

    sessao_vidaas = await _sessao_autorizada(session, user)

    # PDF oficial + hash SHA-256
    laudo = await lme_service.obter(session, laudo_id)
    paciente = await session.get(Paciente, laudo_row.paciente_id)
    medico = await session.get(Profissional, laudo_row.medico_id)
    unidade = await session.get(Unidade, laudo_row.unidade_id)
    pdf = pdf_service.gerar_pdf_lme(laudo, paciente, medico, unidade)
    digest = hashlib.sha256(pdf).digest()

    resultado = await get_provider().assinar_hash(
        sessao_vidaas.access_token or "",
        doc_id=str(laudo_row.id),
        alias=f"LME {laudo.medicamento} — {paciente.nome if paciente else ''}",
        hash_b64=base64.b64encode(digest).decode(),
    )

    assinatura = Assinatura(
        entidade="lme", entidade_id=laudo_row.id,
        assinante_id=user.profissional_id,
        hash_conteudo=digest.hex(), tipo="icp_brasil",
        certificado=resultado["certificado"],
        assinatura_b64=resultado["assinatura_b64"],
        documento_b64=base64.b64encode(pdf).decode(),  # bytes exatos assinados
    )
    session.add(assinatura)
    await session.flush()
    laudo_row.assinatura_id = assinatura.id
    await session.commit()

    return {
        "assinatura_id": str(assinatura.id),
        "tipo": "icp_brasil",
        "hash_sha256": digest.hex(),
        "certificado": resultado["certificado"],
    }


async def baixar_p7s(session: AsyncSession, assinatura_id: str) -> bytes:
    """Assinatura destacada (.p7s) para verificação junto com o PDF."""
    assinatura = await session.get(Assinatura, assinatura_id)
    if assinatura is None or not assinatura.assinatura_b64:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "assinatura não encontrada")
    return base64.b64decode(assinatura.assinatura_b64)


async def baixar_documento(session: AsyncSession, assinatura_id: str) -> bytes:
    """Cópia exata do PDF assinado (par do .p7s na verificação)."""
    assinatura = await session.get(Assinatura, assinatura_id)
    if assinatura is None or not assinatura.documento_b64:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "documento não encontrado")
    return base64.b64decode(assinatura.documento_b64)

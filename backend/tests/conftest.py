"""Fixtures compartilhadas dos testes de integração (requer NEFRON_TEST_DATABASE_URL)."""
from __future__ import annotations

import os
import uuid

import pyotp
import pytest
import pytest_asyncio

TEST_DB = os.getenv("NEFRON_TEST_DATABASE_URL")
if TEST_DB:
    os.environ["NEFRON_DATABASE_URL"] = TEST_DB
    os.environ.setdefault("NEFRON_ENVIRONMENT", "test")


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def medico_ctx():
    """Cria médico + unidade + paciente e devolve dados para login."""
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.core import Paciente, PacienteUnidade, Profissional, Unidade, Vinculo

    email = f"med_{uuid.uuid4().hex[:8]}@nefron.com.br"
    senha = "Nefron@2026"
    async with SessionLocal() as s:
        uni = Unidade(nome="Clínica Teste", cnes=str(uuid.uuid4().int)[:7])
        med = Profissional(nome="Dra. Teste", email=email,
                           senha_hash=hash_password(senha), totp_ativo=False)
        s.add_all([uni, med])
        await s.flush()
        s.add(Vinculo(profissional_id=med.id, unidade_id=uni.id, papel="medico"))
        pac = Paciente(nome="Maria Silva", cns=str(uuid.uuid4().int)[:15],
                       estagio_drc=5, data_nascimento=None)
        s.add(pac)
        await s.flush()
        s.add(PacienteUnidade(paciente_id=pac.id, unidade_id=uni.id))
        await s.commit()
        return {"email": email, "senha": senha,
                "unidade_id": str(uni.id), "paciente_id": str(pac.id)}


async def authenticate(client, ctx) -> dict[str, str]:
    """Executa login→enroll→2FA→contexto e devolve o header Authorization."""
    r = await client.post("/api/v1/auth/login",
                          json={"email": ctx["email"], "senha": ctx["senha"]})
    mfa = r.json()["mfa_token"]
    r = await client.post(f"/api/v1/auth/2fa/enroll?mfa_token={mfa}")
    secret = r.json()["secret"]
    r = await client.post("/api/v1/auth/2fa/verify",
                          json={"mfa_token": mfa, "codigo": pyotp.TOTP(secret).now()})
    refresh = r.json()["refresh_token"]
    r = await client.post("/api/v1/auth/context", json={
        "refresh_token": refresh, "unidade_id": ctx["unidade_id"], "papel": "medico"})
    access = r.json()["access_token"]
    return {"Authorization": f"Bearer {access}"}


@pytest_asyncio.fixture
async def auth_headers(client, medico_ctx):
    headers = await authenticate(client, medico_ctx)
    return headers, medico_ctx

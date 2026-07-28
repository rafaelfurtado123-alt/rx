"""Teste de integração do fluxo de auth + dashboard (requer Postgres de teste).

Ativado por NEFRON_TEST_DATABASE_URL. O schema + adaptações de auth próprio devem
estar aplicados no banco de teste (ver README).
"""
from __future__ import annotations

import os
import uuid

import pyotp
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

TEST_DB = os.getenv("NEFRON_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="defina NEFRON_TEST_DATABASE_URL")

if TEST_DB:
    os.environ["NEFRON_DATABASE_URL"] = TEST_DB


@pytest_asyncio.fixture
async def demo(tmp_path_factory):
    """Cria um médico demo direto no banco e devolve seus dados."""
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
        pac = Paciente(nome="Paciente Teste")
        s.add(pac)
        await s.flush()
        s.add(PacienteUnidade(paciente_id=pac.id, unidade_id=uni.id))
        await s.commit()
        return {"email": email, "senha": senha, "unidade_id": str(uni.id)}


@pytest_asyncio.fixture
async def client():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_full_login_flow(client, demo):
    # Passo 1 — login com senha
    r = await client.post("/api/v1/auth/login",
                          json={"email": demo["email"], "senha": demo["senha"]})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["totp_enrollment_required"] is True
    mfa_token = data["mfa_token"]

    # Enroll TOTP (primeiro acesso)
    r = await client.post(f"/api/v1/auth/2fa/enroll?mfa_token={mfa_token}")
    assert r.status_code == 200, r.text
    secret = r.json()["secret"]

    # Passo 2 — verifica 2FA
    codigo = pyotp.TOTP(secret).now()
    r = await client.post("/api/v1/auth/2fa/verify",
                          json={"mfa_token": mfa_token, "codigo": codigo})
    assert r.status_code == 200, r.text
    verify = r.json()
    assert len(verify["vinculos"]) == 1
    refresh = verify["refresh_token"]

    # Passo 3 — seleciona contexto (unidade + papel)
    r = await client.post("/api/v1/auth/context", json={
        "refresh_token": refresh,
        "unidade_id": demo["unidade_id"],
        "papel": "medico",
    })
    assert r.status_code == 200, r.text
    access = r.json()["access_token"]

    # Dashboard do médico
    r = await client.get("/api/v1/dashboard",
                         headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200, r.text
    dash = r.json()
    assert dash["perfil"] == "medico"
    assert any(m["chave"] == "pacientes_hoje" for m in dash["metricas"])


async def test_wrong_password_is_generic(client, demo):
    r = await client.post("/api/v1/auth/login",
                          json={"email": demo["email"], "senha": "errada!!"})
    assert r.status_code == 401


async def test_dashboard_requires_context(client, demo):
    import datetime as dt

    from app.core.security import create_token
    # access token SEM unidade/papel deve ser barrado
    bad = create_token("x", "access", dt.timedelta(minutes=5))
    r = await client.get("/api/v1/dashboard", headers={"Authorization": f"Bearer {bad}"})
    assert r.status_code == 403

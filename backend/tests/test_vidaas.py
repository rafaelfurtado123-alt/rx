"""Testes de integração da assinatura ICP-Brasil via VIDaaS (provedor simulado).

O provedor mock é ativado automaticamente porque NEFRON_VIDAAS_CLIENT_ID não
está definido no ambiente de teste — o fluxo OAuth2/PKCE, o armazenamento da
sessão e a assinatura do PDF são exercitados de ponta a ponta.
"""
from __future__ import annotations

import hashlib
import os

import pytest

TEST_DB = os.getenv("NEFRON_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="defina NEFRON_TEST_DATABASE_URL")


async def _lme_vigente(client, headers, ctx) -> str:
    """Cria um LME emitido (vigente) reutilizando os helpers do teste de LME."""
    from tests.test_lme import _marcar_paciente_trs, _medicamento_ceaf, _registrar_exame

    pid = ctx["paciente_id"]
    await _marcar_paciente_trs(pid)
    med_id = await _medicamento_ceaf("Alfaepoetina")
    await _registrar_exame(pid, "HB", 9.4)
    await _registrar_exame(pid, "FERR", 180)
    await _registrar_exame(pid, "TSAT", 18)
    r = await client.post(f"/api/v1/pacientes/{pid}/lme", headers=headers,
                          json={"medicamento_id": med_id,
                                "posologia": "4000 UI 3x/semana SC"})
    laudo_id = r.json()["id"]
    r = await client.post(f"/api/v1/lme/{laudo_id}/assinar", headers=headers,
                          json={})
    assert r.status_code == 200, r.text
    return laudo_id


async def test_fluxo_completo_autorizacao_e_assinatura(client, auth_headers):
    headers, ctx = auth_headers
    laudo_id = await _lme_vigente(client, headers, ctx)

    # 1) Inicia a autorização (PKCE) — devolve URL do VIDaaS
    r = await client.post("/api/v1/assinatura/vidaas/autorizacao", headers=headers)
    assert r.status_code == 201, r.text
    auth = r.json()
    assert auth["mock"] is True
    assert "authorization_url" in auth
    state = auth["state"]

    # 2) Status inicial: pendente
    r = await client.get(f"/api/v1/assinatura/vidaas/autorizacao/{state}",
                         headers=headers)
    assert r.json()["status"] == "pendente"

    # 3) Callback do PSC (redirect do navegador — rota pública)
    r = await client.get(
        f"/api/v1/assinatura/vidaas/callback?state={state}&code=COD123")
    assert r.status_code == 200
    assert "Autorização concluída" in r.text

    # 4) Status: autorizada
    r = await client.get(f"/api/v1/assinatura/vidaas/autorizacao/{state}",
                         headers=headers)
    assert r.json()["status"] == "autorizada"

    # 5) Assina o PDF do LME com o certificado em nuvem
    r = await client.post(f"/api/v1/assinatura/vidaas/lme/{laudo_id}",
                          headers=headers)
    assert r.status_code == 201, r.text
    assinatura = r.json()
    assert assinatura["tipo"] == "icp_brasil"
    assert len(assinatura["hash_sha256"]) == 64  # SHA-256 hex
    assert assinatura["certificado"]["origem"] == "vidaas-mock"

    # 6) O hash gravado corresponde EXATAMENTE ao documento assinado armazenado
    aid = assinatura["assinatura_id"]
    r = await client.get(f"/api/v1/assinatura/{aid}/documento", headers=headers)
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")
    assert hashlib.sha256(r.content).hexdigest() == assinatura["hash_sha256"]

    # 6b) PDF determinístico: regenerar o mesmo laudo produz os mesmos bytes
    r2 = await client.get(f"/api/v1/lme/{laudo_id}/pdf", headers=headers)
    assert hashlib.sha256(r2.content).hexdigest() == assinatura["hash_sha256"]

    # 7) Download da assinatura destacada (.p7s)
    r = await client.get(f"/api/v1/assinatura/{aid}/p7s", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pkcs7-signature")
    assert r.content.startswith(b"MOCK-CMS:")


async def test_assinar_sem_autorizacao_falha(client, auth_headers):
    headers, ctx = auth_headers
    laudo_id = await _lme_vigente(client, headers, ctx)
    r = await client.post(f"/api/v1/assinatura/vidaas/lme/{laudo_id}",
                          headers=headers)
    assert r.status_code == 409, r.text
    assert "autorize" in r.json()["detail"].lower()


async def test_assinar_rascunho_falha(client, auth_headers):
    from tests.test_lme import _medicamento_ceaf

    headers, ctx = auth_headers
    med_id = await _medicamento_ceaf("Alfaepoetina")
    # LME rascunho (sem exames → pendências, não emitido)
    r = await client.post(f"/api/v1/pacientes/{ctx['paciente_id']}/lme",
                          headers=headers, json={"medicamento_id": med_id})
    laudo_id = r.json()["id"]

    # Autoriza a sessão para isolar o motivo da falha
    r = await client.post("/api/v1/assinatura/vidaas/autorizacao", headers=headers)
    state = r.json()["state"]
    await client.get(f"/api/v1/assinatura/vidaas/callback?state={state}&code=X")

    r = await client.post(f"/api/v1/assinatura/vidaas/lme/{laudo_id}",
                          headers=headers)
    assert r.status_code == 409
    assert "emita" in r.json()["detail"].lower()


async def test_callback_state_desconhecido(client):
    r = await client.get("/api/v1/assinatura/vidaas/callback?state=inexistente&code=X")
    assert r.status_code == 404


# ------------------- Login por certificado digital -------------------


async def _dar_cpf_ao_medico(ctx) -> str:
    import uuid as _uuid

    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.core import Profissional

    cpf = str(_uuid.uuid4().int)[:11]
    async with SessionLocal() as s:
        prof = await s.scalar(
            select(Profissional).where(Profissional.email == ctx["email"]))
        prof.cpf = cpf
        await s.commit()
    return cpf


async def test_login_por_certificado_fluxo_completo(client, auth_headers):
    _, ctx = auth_headers
    cpf = await _dar_cpf_ao_medico(ctx)

    # 1) Inicia o login por certificado (sem senha/TOTP)
    r = await client.post("/api/v1/auth/vidaas/login", json={"cpf": cpf})
    assert r.status_code == 201, r.text
    state = r.json()["state"]
    assert r.json()["mock"] is True

    # 2) Pendente até a aprovação no app
    r = await client.get(f"/api/v1/auth/vidaas/login/{state}")
    assert r.json()["status"] == "pendente"

    # 3) Aprovação (callback do PSC)
    r = await client.get(
        f"/api/v1/assinatura/vidaas/callback?state={state}&code=CERT")
    assert r.status_code == 200

    # 4) Polling devolve refresh + vínculos (mesmo formato do 2FA)
    r = await client.get(f"/api/v1/auth/vidaas/login/{state}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "autorizada"
    assert len(data["vinculos"]) == 1

    # 5) Sessão é de USO ÚNICO — segundo consumo não devolve tokens
    r = await client.get(f"/api/v1/auth/vidaas/login/{state}")
    assert r.json()["status"] == "expirada"

    # 6) O refresh emitido funciona no fluxo normal de contexto → dashboard
    r = await client.post("/api/v1/auth/context", json={
        "refresh_token": data["refresh_token"],
        "unidade_id": data["vinculos"][0]["unidade_id"],
        "papel": "medico"})
    assert r.status_code == 200, r.text
    access = r.json()["access_token"]
    r = await client.get("/api/v1/dashboard",
                         headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200


async def test_login_certificado_cpf_desconhecido(client):
    r = await client.post("/api/v1/auth/vidaas/login",
                          json={"cpf": "00000000000"})
    assert r.status_code == 404
    r = await client.post("/api/v1/auth/vidaas/login", json={"cpf": "123"})
    assert r.status_code == 400


# ------------------- Receitas (simples e controle especial) -------------------


async def _prescricao_assinada(client, headers, ctx, controlado: bool) -> str:
    import uuid as _uuid

    from app.core.database import SessionLocal
    from app.models.hd import RefMedicamento

    async with SessionLocal() as s:
        med = RefMedicamento(
            principio_ativo=f"{'Clonazepam' if controlado else 'Losartana pot'} "
                            f"{_uuid.uuid4().hex[:4]}",
            apresentacao="comprimido", controlado=controlado)
        s.add(med)
        await s.commit()
        med_id = str(med.id)

    r = await client.post(
        f"/api/v1/pacientes/{ctx['paciente_id']}/prescricoes", headers=headers,
        json={"tipo": "geral", "assinar": True, "itens": [
            {"medicamento_id": med_id, "dose": 2, "unidade_dose": "mg",
             "via": "VO", "frequencia": "1x/dia", "duracao": "30 dias"}]})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _autorizar_vidaas(client, headers) -> None:
    r = await client.post("/api/v1/assinatura/vidaas/autorizacao", headers=headers)
    state = r.json()["state"]
    await client.get(f"/api/v1/assinatura/vidaas/callback?state={state}&code=OK")


async def test_receita_simples_pdf_e_assinatura(client, auth_headers):
    headers, ctx = auth_headers
    prescricao_id = await _prescricao_assinada(client, headers, ctx,
                                               controlado=False)

    r = await client.get(f"/api/v1/prescricoes/{prescricao_id}/receita/pdf",
                         headers=headers)
    assert r.status_code == 200, r.text
    assert r.content.startswith(b"%PDF")
    assert r.headers["x-receita-tipo"] == "simples"

    await _autorizar_vidaas(client, headers)
    r = await client.post(f"/api/v1/assinatura/vidaas/prescricao/{prescricao_id}",
                          headers=headers)
    assert r.status_code == 201, r.text
    assinatura = r.json()
    assert assinatura["receita_tipo"] == "simples"

    # Hash confere com o documento assinado armazenado
    aid = assinatura["assinatura_id"]
    r = await client.get(f"/api/v1/assinatura/{aid}/documento", headers=headers)
    assert hashlib.sha256(r.content).hexdigest() == assinatura["hash_sha256"]


async def test_receita_controlada_em_duas_vias(client, auth_headers):
    headers, ctx = auth_headers
    prescricao_id = await _prescricao_assinada(client, headers, ctx,
                                               controlado=True)

    r = await client.get(f"/api/v1/prescricoes/{prescricao_id}/receita/pdf",
                         headers=headers)
    assert r.status_code == 200
    assert r.headers["x-receita-tipo"] == "controle_especial"

    await _autorizar_vidaas(client, headers)
    r = await client.post(f"/api/v1/assinatura/vidaas/prescricao/{prescricao_id}",
                          headers=headers)
    assert r.status_code == 201, r.text
    assert r.json()["receita_tipo"] == "controle_especial"


async def test_receita_exige_prescricao_assinada(client, auth_headers):
    import uuid as _uuid

    from app.core.database import SessionLocal
    from app.models.hd import RefMedicamento

    headers, ctx = auth_headers
    async with SessionLocal() as s:
        med = RefMedicamento(principio_ativo=f"AAS {_uuid.uuid4().hex[:4]}",
                             apresentacao="100 mg")
        s.add(med)
        await s.commit()
        med_id = str(med.id)

    # Prescrição em rascunho (não assinada)
    r = await client.post(
        f"/api/v1/pacientes/{ctx['paciente_id']}/prescricoes", headers=headers,
        json={"tipo": "geral", "assinar": False,
              "itens": [{"medicamento_id": med_id, "dose": 100}]})
    prescricao_id = r.json()["id"]

    r = await client.get(f"/api/v1/prescricoes/{prescricao_id}/receita/pdf",
                         headers=headers)
    assert r.status_code == 409

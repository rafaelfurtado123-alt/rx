"""Testes de integração: cadastro de pacientes por segmento, ambulatório
conservador (agenda + painel) e login segmentado (equipe multiprofissional)."""
from __future__ import annotations

import datetime as dt
import os
import uuid

import pyotp
import pytest

TEST_DB = os.getenv("NEFRON_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="defina NEFRON_TEST_DATABASE_URL")


def _cns() -> str:
    return str(uuid.uuid4().int)[:15]


# ------------------------- Cadastro de pacientes -------------------------


async def test_cadastro_conservador_e_filtro_por_segmento(client, auth_headers):
    headers, _ = auth_headers

    r = await client.post("/api/v1/pacientes", headers=headers, json={
        "nome": "João Conservador", "cns": _cns(), "sexo": "masculino",
        "data_nascimento": "1955-09-02", "etiologia_drc": "Hipertensão arterial",
        "estagio_drc": 4, "segmento": "conservador"})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["segmento"] == "conservador"
    assert data["idade"] is not None

    # Filtro por segmento: conservador aparece, lista de HD não o inclui
    r = await client.get("/api/v1/pacientes?segmento=conservador", headers=headers)
    nomes = [p["nome"] for p in r.json()]
    assert "João Conservador" in nomes
    r = await client.get("/api/v1/pacientes?segmento=hemodialise", headers=headers)
    assert "João Conservador" not in [p["nome"] for p in r.json()]

    r = await client.get("/api/v1/pacientes?segmento=xpto", headers=headers)
    assert r.status_code == 400


async def test_cadastro_hd_exige_inicio_trs(client, auth_headers):
    headers, _ = auth_headers
    r = await client.post("/api/v1/pacientes", headers=headers, json={
        "nome": "Pedro HD", "cns": _cns(), "segmento": "hemodialise"})
    assert r.status_code == 400
    assert "inicio_trs" in r.json()["detail"]

    r = await client.post("/api/v1/pacientes", headers=headers, json={
        "nome": "Pedro HD", "cns": _cns(), "segmento": "hemodialise",
        "estagio_drc": 5, "inicio_trs": "2025-01-10", "turno_dialise": "tarde"})
    assert r.status_code == 201, r.text
    assert r.json()["segmento"] == "hemodialise"


async def test_transicao_conservador_para_hemodialise(client, auth_headers):
    headers, _ = auth_headers
    r = await client.post("/api/v1/pacientes", headers=headers, json={
        "nome": "Ana Transição", "cns": _cns(), "estagio_drc": 5,
        "segmento": "conservador"})
    pid = r.json()["id"]

    # Sem inicio_trs → 400
    r = await client.patch(f"/api/v1/pacientes/{pid}", headers=headers,
                           json={"segmento": "hemodialise"})
    assert r.status_code == 400

    # Transição completa (paciente inicia TRS)
    r = await client.patch(f"/api/v1/pacientes/{pid}", headers=headers,
                           json={"segmento": "hemodialise",
                                 "inicio_trs": "2026-07-01",
                                 "turno_dialise": "manha"})
    assert r.status_code == 200, r.text
    assert r.json()["segmento"] == "hemodialise"
    assert r.json()["inicio_trs"] == "2026-07-01"


# ------------------------- Ambulatório conservador -------------------------


async def test_consulta_agendar_realizar_e_timeline(client, auth_headers):
    headers, _ = auth_headers
    r = await client.post("/api/v1/pacientes", headers=headers, json={
        "nome": "Carlos Ambulatório", "cns": _cns(), "estagio_drc": 3,
        "segmento": "conservador"})
    pid = r.json()["id"]

    hoje = dt.datetime.now(dt.timezone.utc).replace(hour=14, minute=0)
    r = await client.post(f"/api/v1/pacientes/{pid}/consultas", headers=headers,
                          json={"data_hora": hoje.isoformat(),
                                "tipo": "primeira_consulta"})
    assert r.status_code == 201, r.text
    consulta_id = r.json()["id"]

    # Agenda do dia lista a consulta
    r = await client.get("/api/v1/ambulatorio/consultas", headers=headers)
    assert any(c["id"] == consulta_id for c in r.json())

    # Realizada → cria episódio na timeline
    r = await client.post(f"/api/v1/consultas/{consulta_id}/status",
                          headers=headers, json={"status": "realizada"})
    assert r.status_code == 200, r.text
    assert r.json()["episodio_id"] is not None

    r = await client.get(f"/api/v1/pacientes/{pid}/timeline", headers=headers)
    assert any(i["tipo"] == "episodio" and i["subtipo"] == "consulta"
               for i in r.json())

    # Consulta fechada não reabre
    r = await client.post(f"/api/v1/consultas/{consulta_id}/status",
                          headers=headers, json={"status": "faltou"})
    assert r.status_code == 409


async def test_painel_ambulatorio(client, auth_headers):
    headers, _ = auth_headers
    for estagio in (3, 4, 5):
        await client.post("/api/v1/pacientes", headers=headers, json={
            "nome": f"Paciente E{estagio}", "cns": _cns(),
            "estagio_drc": estagio, "segmento": "conservador"})

    r = await client.get("/api/v1/ambulatorio/painel", headers=headers)
    assert r.status_code == 200, r.text
    painel = r.json()
    assert painel["pacientes_conservador"] == 3
    assert painel["candidatos_preparo_trs"] == 2  # estágios 4 e 5
    assert painel["por_estagio"]["estagio_4"] == 1


# ------------------------- Login segmentado: equipe multi -------------------------


async def _login_com_papel(client, email: str, senha: str, unidade_id: str,
                           papel: str) -> dict[str, str]:
    r = await client.post("/api/v1/auth/login", json={"email": email, "senha": senha})
    mfa = r.json()["mfa_token"]
    r = await client.post(f"/api/v1/auth/2fa/enroll?mfa_token={mfa}")
    secret = r.json()["secret"]
    r = await client.post("/api/v1/auth/2fa/verify",
                          json={"mfa_token": mfa,
                                "codigo": pyotp.TOTP(secret).now()})
    refresh = r.json()["refresh_token"]
    r = await client.post("/api/v1/auth/context", json={
        "refresh_token": refresh, "unidade_id": unidade_id, "papel": papel})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_login_equipe_multi_dashboard_e_permissoes(client, auth_headers):
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.core import Profissional, Vinculo

    headers_medico, ctx = auth_headers
    email = f"nut_{uuid.uuid4().hex[:8]}@nefron.com.br"
    senha = "Nefron@2026"
    async with SessionLocal() as s:
        prof = Profissional(nome="Nut. Teste", email=email,
                            conselho_tipo="CRN",
                            senha_hash=hash_password(senha), totp_ativo=False)
        s.add(prof)
        await s.flush()
        s.add(Vinculo(profissional_id=prof.id, unidade_id=ctx["unidade_id"],
                      papel="equipe_multi"))
        await s.commit()

    headers = await _login_com_papel(client, email, senha,
                                     ctx["unidade_id"], "equipe_multi")

    # Dashboard do segmento equipe_multi
    r = await client.get("/api/v1/dashboard", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["perfil"] == "equipe_multi"
    assert any(m["chave"] == "evolucoes_pendentes" for m in r.json()["metricas"])

    # PODE registrar evolução da própria categoria (nutrição)
    r = await client.post(f"/api/v1/pacientes/{ctx['paciente_id']}/evolucoes",
                          headers=headers,
                          json={"categoria": "nutricao",
                                "avaliacao": "Aporte proteico adequado.",
                                "plano": "Manter orientação."})
    assert r.status_code == 201, r.text

    # NÃO pode prescrever (ato médico/enfermagem) nem gerar LME (ato médico)
    r = await client.post(f"/api/v1/pacientes/{ctx['paciente_id']}/prescricoes",
                          headers=headers,
                          json={"tipo": "geral",
                                "itens": [{"descricao_livre": "dieta"}]})
    assert r.status_code == 403
    r = await client.post(f"/api/v1/pacientes/{ctx['paciente_id']}/lme",
                          headers=headers,
                          json={"medicamento_id": str(uuid.uuid4())})
    assert r.status_code == 403

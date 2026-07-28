"""Testes de integração do prontuário: header, timeline, evolução, exames, IA."""
from __future__ import annotations

import datetime as dt
import os
import uuid

import pytest

TEST_DB = os.getenv("NEFRON_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="defina NEFRON_TEST_DATABASE_URL")


async def _seed_exames(paciente_id: str):
    """Cria um exame de referência (Hb) e dois resultados para o paciente."""
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.clinico import ExameResultado, RefExame

    async with SessionLocal() as s:
        ref = await s.scalar(select(RefExame).where(RefExame.codigo == "HB"))
        if ref is None:
            ref = RefExame(codigo="HB", nome="Hemoglobina", unidade="g/dL",
                           ref_min=10, ref_max=12, categoria="hematologia")
            s.add(ref)
            await s.flush()
        base = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
        s.add_all([
            ExameResultado(paciente_id=paciente_id, exame_id=ref.id, valor=11.0,
                           unidade="g/dL", data_coleta=base, fora_faixa=False),
            ExameResultado(paciente_id=paciente_id, exame_id=ref.id, valor=9.4,
                           unidade="g/dL", data_coleta=base + dt.timedelta(days=30),
                           fora_faixa=True),
        ])
        await s.commit()


async def test_header_do_paciente(client, auth_headers):
    headers, ctx = auth_headers
    r = await client.get(f"/api/v1/pacientes/{ctx['paciente_id']}", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["nome"] == "Maria Silva"
    assert r.json()["estagio_drc"] == 5


async def test_criar_e_listar_evolucao(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    r = await client.post(f"/api/v1/pacientes/{pid}/evolucoes", headers=headers, json={
        "categoria": "medica",
        "subjetivo": "Refere melhora da dispneia.",
        "avaliacao": "DRC estágio 5 em HD, anemia em investigação.",
        "plano": "Ajustar eritropoetina.",
        "assinar": True,
    })
    assert r.status_code == 201, r.text
    assert r.json()["assinada_em"] is not None

    r = await client.get(f"/api/v1/pacientes/{pid}/evolucoes", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_evolucao_vazia_rejeitada(client, auth_headers):
    headers, ctx = auth_headers
    r = await client.post(f"/api/v1/pacientes/{ctx['paciente_id']}/evolucoes",
                          headers=headers, json={"categoria": "medica"})
    assert r.status_code == 400


async def test_serie_exame_e_tendencia(client, auth_headers):
    headers, ctx = auth_headers
    await _seed_exames(ctx["paciente_id"])
    r = await client.get(f"/api/v1/pacientes/{ctx['paciente_id']}/exames/HB",
                         headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["codigo"] == "HB"
    assert data["ultimo_valor"] == 9.4
    assert data["tendencia"] == "down"  # 11.0 -> 9.4
    assert len(data["pontos"]) == 2
    assert data["ref_min"] == 10 and data["ref_max"] == 12


async def test_timeline_unificada(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    await _seed_exames(pid)
    await client.post(f"/api/v1/pacientes/{pid}/evolucoes", headers=headers,
                      json={"categoria": "medica", "plano": "Manter conduta."})
    r = await client.get(f"/api/v1/pacientes/{pid}/timeline", headers=headers)
    assert r.status_code == 200, r.text
    tipos = {i["tipo"] for i in r.json()}
    assert "exame" in tipos and "evolucao" in tipos


async def test_resumo_ia_e_rascunho(client, auth_headers):
    headers, _ = auth_headers
    fake_pid = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/pacientes/{fake_pid}/evolucoes/resumo-ia", headers=headers,
        json={"subjetivo": "Dor lombar há 2 dias", "plano": "Analgesia"})
    assert r.status_code == 200, r.text
    assert r.json()["rascunho"] is True
    assert len(r.json()["resumo"]) > 0

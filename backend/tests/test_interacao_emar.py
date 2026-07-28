"""Testes de integração: interação medicamentosa e eMAR."""
from __future__ import annotations

import os
import uuid

import pytest

TEST_DB = os.getenv("NEFRON_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="defina NEFRON_TEST_DATABASE_URL")


async def _med(principio: str) -> str:
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.hd import RefMedicamento

    async with SessionLocal() as s:
        med = await s.scalar(select(RefMedicamento)
                             .where(RefMedicamento.principio_ativo == principio))
        if med is None:
            med = RefMedicamento(principio_ativo=principio, apresentacao="comprimido")
            s.add(med)
            await s.commit()
        return str(med.id)


# ------------------------- Interação medicamentosa -------------------------


async def test_interacao_grave_alerta_na_mesma_prescricao(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    espiro = await _med("Espironolactona")
    losartana = await _med("Losartana")

    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes", headers=headers,
                          json={"tipo": "geral", "assinar": True, "itens": [
                              {"medicamento_id": espiro, "dose": 25},
                              {"medicamento_id": losartana, "dose": 50},
                          ]})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "ativa"  # grave alerta, não bloqueia
    alertas = [a for i in data["itens"] for a in i["alertas"]
               if a["tipo"] == "interacao"]
    assert len(alertas) >= 2  # aparece nos dois itens
    assert any("hipercalemia" in a["mensagem"].lower() for a in alertas)


async def test_interacao_contraindicada_bloqueia(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    espiro = await _med("Espironolactona")
    kcl = await _med("Cloreto de potássio")

    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes", headers=headers,
                          json={"tipo": "geral", "assinar": True, "itens": [
                              {"medicamento_id": espiro, "dose": 25},
                              {"medicamento_id": kcl, "dose": 600},
                          ]})
    assert r.status_code == 409, r.text

    # Rascunho permitido, marcado como bloqueado
    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes", headers=headers,
                          json={"tipo": "geral", "assinar": False, "itens": [
                              {"medicamento_id": espiro, "dose": 25},
                              {"medicamento_id": kcl, "dose": 600},
                          ]})
    assert r.status_code == 201
    assert r.json()["bloqueada"] is True


async def test_interacao_contra_prescricao_ativa(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    calcio = await _med("Carbonato de cálcio")
    calcitriol = await _med("Calcitriol")

    # 1ª prescrição ativa com cálcio
    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes", headers=headers,
                          json={"tipo": "geral", "assinar": True, "itens": [
                              {"medicamento_id": calcio, "dose": 500}]})
    assert r.status_code == 201, r.text

    # Nova prescrição de calcitriol → interage com o cálcio EM USO
    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes", headers=headers,
                          json={"tipo": "geral", "assinar": True, "itens": [
                              {"medicamento_id": calcitriol, "dose": 0.25}]})
    assert r.status_code == 201, r.text
    alertas = r.json()["itens"][0]["alertas"]
    assert any(a["tipo"] == "interacao" and "em uso" in a["mensagem"]
               for a in alertas)


# ------------------------- eMAR -------------------------


async def test_emar_gerado_automaticamente_ao_assinar(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    med = await _med(f"Cefepima {uuid.uuid4().hex[:4]}")

    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes", headers=headers,
                          json={"tipo": "geral", "assinar": True, "itens": [
                              {"medicamento_id": med, "dose": 1,
                               "unidade_dose": "g", "via": "IV",
                               "frequencia": "8/8h"}]})
    assert r.status_code == 201, r.text

    r = await client.get(f"/api/v1/pacientes/{pid}/emar?pendentes=true",
                         headers=headers)
    assert r.status_code == 200
    doses = [e for e in r.json() if e["medicamento"] and "Cefepima" in e["medicamento"]]
    assert len(doses) == 3  # 8/8h em 24h


async def test_emar_registrar_administracao_e_fechamento(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    med = await _med(f"Vancomicina {uuid.uuid4().hex[:4]}")

    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes", headers=headers,
                          json={"tipo": "geral", "assinar": True, "itens": [
                              {"medicamento_id": med, "dose": 1, "via": "IV",
                               "frequencia": "1x/dia"}]})
    assert r.status_code == 201

    r = await client.get(f"/api/v1/pacientes/{pid}/emar?pendentes=true",
                         headers=headers)
    dose = next(e for e in r.json()
                if e["medicamento"] and "Vancomicina" in e["medicamento"])

    # Administra com lote
    r = await client.post(f"/api/v1/emar/{dose['id']}/registrar", headers=headers,
                          json={"status": "administrado", "lote": "L-2026-07"})
    assert r.status_code == 200, r.text
    reg = r.json()
    assert reg["status"] == "administrado"
    assert reg["horario_realizado"] is not None
    assert reg["lote"] == "L-2026-07"

    # Fechado não reabre
    r = await client.post(f"/api/v1/emar/{dose['id']}/registrar", headers=headers,
                          json={"status": "recusado"})
    assert r.status_code == 409


async def test_emar_frequencia_livre_exige_agendamento_manual(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    med = await _med(f"Dipirona SN {uuid.uuid4().hex[:4]}")

    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes", headers=headers,
                          json={"tipo": "geral", "assinar": True, "itens": [
                              {"medicamento_id": med, "dose": 500,
                               "frequencia": "se dor"}]})
    assert r.status_code == 201
    item_id = r.json()["itens"][0]["id"]

    # Nada agendado automaticamente para "se dor"
    r = await client.get(f"/api/v1/pacientes/{pid}/emar?pendentes=true",
                         headers=headers)
    assert not any(e["prescricao_item_id"] == item_id for e in r.json())

    # Agenda manualmente
    r = await client.post(f"/api/v1/pacientes/{pid}/emar", headers=headers,
                          json={"prescricao_item_id": item_id,
                                "horarios": ["2026-07-28T14:00:00Z"]})
    assert r.status_code == 201
    assert len(r.json()) == 1

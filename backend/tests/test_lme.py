"""Testes de integração do LME Inteligente (motor PCDT + validade + renovação + PDF)."""
from __future__ import annotations

import datetime as dt
import os

import pytest

TEST_DB = os.getenv("NEFRON_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="defina NEFRON_TEST_DATABASE_URL")


async def _medicamento_ceaf(principio: str) -> str:
    """Busca um medicamento CEAF do seed pelo princípio ativo."""
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.hd import RefMedicamento

    async with SessionLocal() as s:
        med = await s.scalar(select(RefMedicamento)
                             .where(RefMedicamento.principio_ativo == principio))
        assert med is not None, f"seed.sql deve conter {principio}"
        return str(med.id)


async def _registrar_exame(paciente_id: str, codigo: str, valor: float,
                           dias_atras: int = 0):
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.clinico import ExameResultado, RefExame

    async with SessionLocal() as s:
        ref = await s.scalar(select(RefExame).where(RefExame.codigo == codigo))
        assert ref is not None
        s.add(ExameResultado(
            paciente_id=paciente_id, exame_id=ref.id, valor=valor,
            data_coleta=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=dias_atras)))
        await s.commit()


async def _marcar_paciente_trs(paciente_id: str):
    from app.core.database import SessionLocal
    from app.models.core import Paciente

    async with SessionLocal() as s:
        p = await s.get(Paciente, paciente_id)
        p.inicio_trs = dt.date(2022, 6, 1)
        p.etiologia_drc = "Nefropatia diabética"
        await s.commit()


async def test_lme_sem_exames_fica_pendente_e_nao_emite(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    med_id = await _medicamento_ceaf("Alfaepoetina")

    r = await client.post(f"/api/v1/pacientes/{pid}/lme", headers=headers,
                          json={"medicamento_id": med_id,
                                "posologia": "4000 UI 3x/semana SC"})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "rascunho"
    assert data["pcdt_nome"] == "Anemia na Doença Renal Crônica"
    # Sem Hb/Ferritina/TSAT registrados → 3 pendências
    assert len(data["pendencias"]) == 3

    # Emitir com pendência → 409
    r = await client.post(f"/api/v1/lme/{data['id']}/assinar", headers=headers,
                          json={})
    assert r.status_code == 409, r.text
    assert "pendências" in r.json()["detail"]


async def test_lme_completo_autopreenche_emite_e_gera_pdf(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    await _marcar_paciente_trs(pid)
    med_id = await _medicamento_ceaf("Alfaepoetina")

    # Exames obrigatórios do PCDT de anemia, com Hb fora da meta (9.4 < 10)
    await _registrar_exame(pid, "HB", 9.4)
    await _registrar_exame(pid, "FERR", 180)
    await _registrar_exame(pid, "TSAT", 18)

    r = await client.post(f"/api/v1/pacientes/{pid}/lme", headers=headers,
                          json={"medicamento_id": med_id,
                                "posologia": "4000 UI 3x/semana SC",
                                "quantidade_mes": 12})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["pendencias"] == []
    # Autopreenchimento: paciente em TRS → CID N18.6; D63.1 como secundário
    assert data["cid_principal"] == "N18.6"
    assert "D63.1" in data["cids_secundarios"]
    # Justificativa ancorada nos valores reais (guardrail: cita 9.4)
    assert "9.4" in data["justificativa"]
    assert "PCDT" in data["justificativa"]
    # Anamnese cita TRS e etiologia
    assert "hemodiálise" in data["anamnese"].lower()
    assert "nefropatia diabética" in data["anamnese"].lower()

    # Assina/emite → vigente com validade de 90 dias
    r = await client.post(f"/api/v1/lme/{data['id']}/assinar", headers=headers,
                          json={"aceite_termo_por": "Maria Silva"})
    assert r.status_code == 200, r.text
    emitido = r.json()
    assert emitido["status"] == "vigente"
    assert emitido["dias_restantes"] in (89, 90)

    # PDFs do LME e do TER
    r = await client.get(f"/api/v1/lme/{data['id']}/pdf", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    r = await client.get(f"/api/v1/lme/{data['id']}/termo/pdf", headers=headers)
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")


async def test_exame_vencido_gera_pendencia(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    med_id = await _medicamento_ceaf("Alfaepoetina")

    await _registrar_exame(pid, "HB", 9.8, dias_atras=120)  # > 90 dias → vencido
    await _registrar_exame(pid, "FERR", 300)
    await _registrar_exame(pid, "TSAT", 25)

    r = await client.post(f"/api/v1/pacientes/{pid}/lme", headers=headers,
                          json={"medicamento_id": med_id})
    assert r.status_code == 201
    data = r.json()
    assert any("vencido" in p for p in data["pendencias"])
    hb = next(e for e in data["exames"] if e["codigo"] == "HB")
    assert hb["situacao"] == "vencido"


async def test_renovacao_um_clique_encadeia(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    await _marcar_paciente_trs(pid)
    med_id = await _medicamento_ceaf("Sevelâmer (cloridrato)")

    # Exames do PCDT DMO-DRC, com fósforo alto (6.8 > 5.5)
    await _registrar_exame(pid, "PTH", 700)
    await _registrar_exame(pid, "CA", 9.0)
    await _registrar_exame(pid, "P", 6.8)

    r = await client.post(f"/api/v1/pacientes/{pid}/lme", headers=headers,
                          json={"medicamento_id": med_id,
                                "posologia": "800 mg 3x/dia"})
    assert r.status_code == 201, r.text
    origem = r.json()
    assert origem["pcdt_nome"].startswith("Distúrbio Mineral")
    assert "6.8" in origem["justificativa"]  # fósforo citado

    r = await client.post(f"/api/v1/lme/{origem['id']}/assinar", headers=headers,
                          json={})
    assert r.status_code == 200

    # Renovação em 1 clique
    r = await client.post(f"/api/v1/lme/{origem['id']}/renovar", headers=headers)
    assert r.status_code == 201, r.text
    novo = r.json()
    assert novo["laudo_anterior_id"] == origem["id"]
    assert novo["posologia"] == "800 mg 3x/dia"  # herdada
    assert novo["status"] == "rascunho"          # reavaliado, pronto p/ assinar

    # Origem passou a 'renovado'
    r = await client.get(f"/api/v1/lme/{origem['id']}", headers=headers)
    assert r.json()["status"] == "renovado"

    # Histórico lista os dois
    r = await client.get(f"/api/v1/pacientes/{pid}/lme", headers=headers)
    assert len(r.json()) >= 2


async def test_medicamento_sem_lme_rejeitado(client, auth_headers):
    from app.core.database import SessionLocal
    from app.models.hd import RefMedicamento

    headers, ctx = auth_headers
    async with SessionLocal() as s:
        med = RefMedicamento(principio_ativo="Paracetamol comum",
                             apresentacao="500 mg", requer_lme=False)
        s.add(med)
        await s.commit()
        med_id = str(med.id)

    r = await client.post(f"/api/v1/pacientes/{ctx['paciente_id']}/lme",
                          headers=headers, json={"medicamento_id": med_id})
    assert r.status_code == 400

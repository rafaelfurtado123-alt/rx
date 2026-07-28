"""Testes de integração: prescrição (checagens), prescrição de HD e sessão completa."""
from __future__ import annotations

import os
import uuid

import pytest

TEST_DB = os.getenv("NEFRON_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="defina NEFRON_TEST_DATABASE_URL")


async def _criar_medicamento(**kwargs) -> str:
    from app.core.database import SessionLocal
    from app.models.hd import RefMedicamento

    async with SessionLocal() as s:
        med = RefMedicamento(
            principio_ativo=kwargs.get("principio_ativo", f"Fármaco {uuid.uuid4().hex[:6]}"),
            apresentacao=kwargs.get("apresentacao", "comprimido"),
            dose_maxima_dia=kwargs.get("dose_maxima_dia"),
            unidade_dose=kwargs.get("unidade_dose", "mg"),
            ajuste_renal=kwargs.get("ajuste_renal"),
        )
        s.add(med)
        await s.commit()
        return str(med.id)


async def _criar_alergia(paciente_id: str, substancia: str, gravidade: str):
    from app.core.database import SessionLocal
    from app.models.clinico import Alergia

    async with SessionLocal() as s:
        s.add(Alergia(paciente_id=paciente_id, substancia=substancia,
                      gravidade=gravidade))
        await s.commit()


# ------------------------- Prescrição geral -------------------------


async def test_alergia_grave_bloqueia_assinatura(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    med_id = await _criar_medicamento(principio_ativo="Dipirona sódica")
    await _criar_alergia(pid, "Dipirona", "grave")

    # Assinar com alergia grave → 409
    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes", headers=headers,
                          json={"tipo": "geral", "assinar": True,
                                "itens": [{"medicamento_id": med_id, "dose": 500}]})
    assert r.status_code == 409, r.text

    # Rascunho é permitido, mas vem marcado como bloqueado com o alerta
    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes", headers=headers,
                          json={"tipo": "geral", "assinar": False,
                                "itens": [{"medicamento_id": med_id, "dose": 500}]})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["bloqueada"] is True
    alertas = data["itens"][0]["alertas"]
    assert any(a["tipo"] == "alergia" and a["gravidade"] == "bloqueio" for a in alertas)


async def test_dose_maxima_gera_alerta(client, auth_headers):
    headers, ctx = auth_headers
    med_id = await _criar_medicamento(dose_maxima_dia=100)
    r = await client.post(f"/api/v1/pacientes/{ctx['paciente_id']}/prescricoes",
                          headers=headers,
                          json={"tipo": "geral", "assinar": True,
                                "itens": [{"medicamento_id": med_id, "dose": 250,
                                           "unidade_dose": "mg"}]})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "ativa"  # alerta não bloqueia
    assert any(a["tipo"] == "dose_maxima" for a in data["itens"][0]["alertas"])


async def test_ajuste_renal_por_tfg(client, auth_headers):
    import datetime as dt

    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.clinico import ExameResultado, RefExame

    headers, ctx = auth_headers
    pid = ctx["paciente_id"]

    # TFG de 12 mL/min registrada para o paciente
    async with SessionLocal() as s:
        ref = await s.scalar(select(RefExame).where(RefExame.codigo == "TFG"))
        assert ref is not None, "seed.sql deve estar aplicado"
        s.add(ExameResultado(paciente_id=pid, exame_id=ref.id, valor=12,
                             data_coleta=dt.datetime.now(dt.timezone.utc)))
        await s.commit()

    med_id = await _criar_medicamento(ajuste_renal=[
        {"tfg_max": 15, "ajuste": "reduzir dose em 50%"},
        {"tfg_max": 30, "ajuste": "reduzir dose em 25%"},
    ])
    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes", headers=headers,
                          json={"tipo": "geral",
                                "itens": [{"medicamento_id": med_id, "dose": 10}]})
    assert r.status_code == 201, r.text
    item = r.json()["itens"][0]
    assert item["ajuste_renal_aplicado"] is True
    assert any("50%" in a["mensagem"] for a in item["alertas"])


# ------------------------- Prescrição de HD -------------------------


async def test_prescricao_hd_volume_calculado_e_assinatura(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]

    r = await client.post(f"/api/v1/pacientes/{pid}/acessos", headers=headers,
                          json={"tipo": "fav", "lado": "esquerdo",
                                "localizacao": "radiocefálica"})
    assert r.status_code == 201, r.text
    acesso_id = r.json()["id"]

    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes-hd", headers=headers,
                          json={
                              "modalidade": "IHD", "duracao_min": 240,
                              "qb_ml_min": 350, "qd_ml_min": 500,
                              "dialisador_modelo": "FX80",
                              "acesso_id": acesso_id,
                              "peso_atual_kg": 72.5, "peso_seco_kg": 70.0,
                              "uf_prescrita_l": 2.5, "uf_maxima_l": 3.0,
                              "perfil_sodio": {"tipo": "ramp", "ini": 145, "fim": 138},
                              "perfil_bicarbonato": {"valor": 32},
                              "heparinizacao": {"tipo": "sistemica",
                                                "bolus_ui": 2000, "manutencao_ui_h": 500},
                              "assinar": True,
                          })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "ativa"
    assert data["volume_calculado_l"] == 2.5  # coluna gerada no banco
    assert data["assinada_em"] is not None


async def test_prescricao_hd_uf_acima_maxima_bloqueia(client, auth_headers):
    headers, ctx = auth_headers
    r = await client.post(
        f"/api/v1/pacientes/{ctx['paciente_id']}/prescricoes-hd", headers=headers,
        json={"modalidade": "IHD", "duracao_min": 240,
              "uf_prescrita_l": 4.0, "uf_maxima_l": 3.0, "assinar": True})
    assert r.status_code == 409, r.text


# ------------------------- Sessão de HD (ciclo completo) -------------------------


async def test_ciclo_completo_da_sessao(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]

    # Prescrição de HD base
    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes-hd", headers=headers,
                          json={"modalidade": "IHD", "duracao_min": 240,
                                "peso_atual_kg": 72.5, "peso_seco_kg": 70.0,
                                "uf_prescrita_l": 2.5, "assinar": True})
    hd_id = r.json()["id"]

    # 1) Recepção — peso pré 75.5 = ganho de 5.5kg (7.9% > 5%) → alerta
    r = await client.post(f"/api/v1/pacientes/{pid}/sessoes", headers=headers,
                          json={"prescricao_hd_id": hd_id, "peso_pre_kg": 75.5,
                                "pa_pre": "140/85", "fc_pre": 78, "temp_pre": 36.2})
    assert r.status_code == 201, r.text
    sessao = r.json()
    assert any(a["tipo"] == "ganho_interdialitico" for a in sessao["alertas"])
    sid = sessao["id"]

    # 2) Início
    r = await client.post(f"/api/v1/sessoes/{sid}/iniciar?maquina=M03",
                          headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["inicio"] is not None

    # 3) Parâmetro intradialítico
    r = await client.post(f"/api/v1/sessoes/{sid}/parametros", headers=headers,
                          json={"pa": "128/80", "fc": 76, "ptm": 145,
                                "fluxo_uf": 0.6})
    assert r.status_code == 201, r.text

    # 4) Intercorrência
    r = await client.post(f"/api/v1/sessoes/{sid}/intercorrencias", headers=headers,
                          json={"tipo": "hipotensao",
                                "descricao": "PA 90/60 na 2ª hora",
                                "conduta": "Trendelenburg + SF 250 mL"})
    assert r.status_code == 201, r.text

    # 5) Encerramento com ureias → adequação automática (usa duração prescrita
    #    de 240 min porque a duração real do teste é ~0)
    r = await client.post(f"/api/v1/sessoes/{sid}/encerrar", headers=headers,
                          json={"peso_pos_kg": 73.0, "ureia_pre": 150,
                                "ureia_pos": 50})
    assert r.status_code == 200, r.text
    fim = r.json()
    assert fim["uf_real_l"] == 2.5  # 75.5 − 73.0
    assert fim["ktv"] == pytest.approx(1.30, abs=0.05)
    assert fim["urr"] == pytest.approx(66.7, abs=0.2)
    assert fim["npcr"] is not None

    # 6) Encerrar de novo → 409
    r = await client.post(f"/api/v1/sessoes/{sid}/encerrar", headers=headers,
                          json={"peso_pos_kg": 73.0})
    assert r.status_code == 409


async def test_parametro_exige_sessao_em_andamento(client, auth_headers):
    headers, ctx = auth_headers
    r = await client.post(f"/api/v1/pacientes/{ctx['paciente_id']}/sessoes",
                          headers=headers, json={"peso_pre_kg": 70.0})
    sid = r.json()["id"]
    # Sem iniciar → 409
    r = await client.post(f"/api/v1/sessoes/{sid}/parametros", headers=headers,
                          json={"pa": "120/80"})
    assert r.status_code == 409

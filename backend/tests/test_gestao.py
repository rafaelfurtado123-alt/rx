"""Testes de integração: escala de diálise, relatórios e faturamento SUS."""
from __future__ import annotations

import datetime as dt
import os

import pytest

TEST_DB = os.getenv("NEFRON_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="defina NEFRON_TEST_DATABASE_URL")


# ------------------------- Escala -------------------------


async def test_escala_criar_e_conflito_de_maquina(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]

    r = await client.post(f"/api/v1/pacientes/{pid}/escala", headers=headers,
                          json={"turno": "manha", "dias_semana": [1, 3, 5],
                                "maquina": "M03"})
    assert r.status_code == 201, r.text
    assert r.json()["dias_semana"] == [1, 3, 5]

    # Mesma máquina/turno com dia em comum → 409
    r = await client.post(f"/api/v1/pacientes/{pid}/escala", headers=headers,
                          json={"turno": "manha", "dias_semana": [5, 6],
                                "maquina": "M03"})
    assert r.status_code == 409, r.text

    # Mesma máquina em dias livres (terça/quinta) → ok
    r = await client.post(f"/api/v1/pacientes/{pid}/escala", headers=headers,
                          json={"turno": "manha", "dias_semana": [2, 4],
                                "maquina": "M03"})
    assert r.status_code == 201, r.text


async def test_escala_do_dia_agrupa_por_turno(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    # Escala em todos os dias para o teste ser estável em qualquer dia da semana
    await client.post(f"/api/v1/pacientes/{pid}/escala", headers=headers,
                      json={"turno": "tarde",
                            "dias_semana": [1, 2, 3, 4, 5, 6, 7]})

    r = await client.get("/api/v1/escala/dia", headers=headers)
    assert r.status_code == 200, r.text
    dia = r.json()
    assert dia["dia_semana"] == dt.date.today().isoweekday()
    nomes = [v["paciente_nome"] for v in dia["turnos"]["tarde"]]
    assert "Maria Silva" in nomes


async def test_escala_dias_invalidos(client, auth_headers):
    headers, ctx = auth_headers
    r = await client.post(f"/api/v1/pacientes/{ctx['paciente_id']}/escala",
                          headers=headers,
                          json={"turno": "manha", "dias_semana": [0, 8]})
    assert r.status_code == 400


# ------------------------- Relatórios -------------------------


async def _sessao_completa(client, headers, pid, ureia_pos=50.0):
    """Cria uma sessão encerrada (com Kt/V calculado)."""
    r = await client.post(f"/api/v1/pacientes/{pid}/prescricoes-hd",
                          headers=headers,
                          json={"modalidade": "IHD", "duracao_min": 240,
                                "peso_atual_kg": 72.0, "peso_seco_kg": 70.0,
                                "assinar": True})
    hd_id = r.json()["id"]
    r = await client.post(f"/api/v1/pacientes/{pid}/sessoes", headers=headers,
                          json={"prescricao_hd_id": hd_id, "peso_pre_kg": 72.0})
    sid = r.json()["id"]
    await client.post(f"/api/v1/sessoes/{sid}/iniciar", headers=headers)
    r = await client.post(f"/api/v1/sessoes/{sid}/encerrar", headers=headers,
                          json={"peso_pos_kg": 70.0, "ureia_pre": 150,
                                "ureia_pos": ureia_pos})
    return r.json()


async def test_censo_e_indicadores(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]

    # Escala + acesso FAV + 2 sessões (Kt/V 1.3 e ~0.6) + Hb na meta
    await client.post(f"/api/v1/pacientes/{pid}/escala", headers=headers,
                      json={"turno": "manha", "dias_semana": [1, 3, 5]})
    await client.post(f"/api/v1/pacientes/{pid}/acessos", headers=headers,
                      json={"tipo": "fav", "lado": "esquerdo"})
    s1 = await _sessao_completa(client, headers, pid, ureia_pos=50)   # Kt/V ~1.30
    s2 = await _sessao_completa(client, headers, pid, ureia_pos=100)  # Kt/V baixo
    assert s1["ktv"] >= 1.2 and s2["ktv"] < 1.2

    from tests.test_lme import _registrar_exame
    await _registrar_exame(pid, "HB", 11.0)

    # Censo
    r = await client.get("/api/v1/relatorios/censo", headers=headers)
    assert r.status_code == 200, r.text
    censo = r.json()
    assert censo["pacientes_ativos"] == 1
    assert censo["em_escala_hd"] == 1
    assert censo["sessoes_30d"] == 2

    # Indicadores
    r = await client.get("/api/v1/relatorios/indicadores", headers=headers)
    assert r.status_code == 200, r.text
    ind = {i["chave"]: i for i in r.json()["indicadores"]}
    assert ind["ktv_adequado"]["valor"] == 50.0        # 1 de 2 sessões
    assert ind["hb_na_meta"]["valor"] == 100.0         # Hb 11.0 na meta
    assert ind["fav_pct"]["valor"] == 100.0            # único acesso é FAV
    assert ind["intercorrencias_100_sessoes"]["denominador"] == 2


# ------------------------- Faturamento -------------------------


async def test_producao_mensal_idempotente_e_csv(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]

    # 2 sessões encerradas neste mês
    await _sessao_completa(client, headers, pid)
    await _sessao_completa(client, headers, pid)

    comp = dt.date.today().strftime("%Y-%m")
    r = await client.post(f"/api/v1/fatura/producao?competencia={comp}",
                          headers=headers)
    assert r.status_code == 200, r.text
    resumo = r.json()
    assert resumo["contas_criadas"] == 1
    assert resumo["sessoes_faturadas"] == 2

    # Re-executar não duplica
    r = await client.post(f"/api/v1/fatura/producao?competencia={comp}",
                          headers=headers)
    assert r.json()["contas_criadas"] == 0
    assert r.json()["contas_existentes"] == 1

    # Conta lista o item de hemodiálise com quantidade 2
    r = await client.get(f"/api/v1/fatura/contas?competencia={comp}",
                         headers=headers)
    contas = r.json()
    assert len(contas) == 1
    assert contas[0]["itens"][0]["sigtap_codigo"] == "0305010107"
    assert contas[0]["itens"][0]["quantidade"] == 2

    # CSV de conferência
    r = await client.get(f"/api/v1/fatura/contas/export?competencia={comp}",
                         headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "0305010107" in r.text
    assert "Maria Silva" in r.text


async def test_apac_criacao_e_validade(client, auth_headers):
    headers, ctx = auth_headers
    pid = ctx["paciente_id"]
    comp = dt.date.today().replace(day=1)

    r = await client.post(f"/api/v1/pacientes/{pid}/apac", headers=headers,
                          json={"competencia": comp.isoformat(),
                                "cid": "N18.6", "validade_meses": 3})
    assert r.status_code == 201, r.text
    apac = r.json()
    assert apac["numero"].startswith("APAC")
    assert apac["procedimento"] == "0305010107"
    ini = dt.date.fromisoformat(apac["validade_ini"])
    fim = dt.date.fromisoformat(apac["validade_fim"])
    assert (fim - ini).days >= 85  # ~3 competências

    r = await client.get(f"/api/v1/pacientes/{pid}/apac", headers=headers)
    assert len(r.json()) == 1
    assert r.json()[0]["status"] == "ativa"


async def test_competencia_invalida(client, auth_headers):
    headers, _ = auth_headers
    r = await client.post("/api/v1/fatura/producao?competencia=julho",
                          headers=headers)
    assert r.status_code == 400

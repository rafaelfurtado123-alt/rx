"""Testes dos cálculos clínicos (puros, sem banco)."""
from __future__ import annotations

import pytest

from app.domain import calculos


def test_ktv_daugirdas_exemplo_realista():
    # ureia_pré 150, pós 50, 4h, UF 2.5L, peso pós 70kg → Kt/V ~1.30
    ktv = calculos.ktv_daugirdas(150, 50, 4, 2.5, 70)
    assert ktv == pytest.approx(1.30, abs=0.02)


def test_urr():
    assert calculos.urr(150, 50) == pytest.approx(66.7, abs=0.1)
    assert calculos.urr(0, 50) is None


def test_volume_uf_nao_negativo():
    assert calculos.volume_uf(72.5, 70.0) == 2.5
    assert calculos.volume_uf(69.0, 70.0) == 0.0


def test_adequacao_agrega_tudo():
    a = calculos.adequacao(150, 50, 4, 2.5, 70)
    assert a.ktv is not None and a.urr is not None and a.npcr is not None


def test_ktv_invalido_retorna_none():
    assert calculos.ktv_daugirdas(0, 50, 4, 2.5, 70) is None
    assert calculos.ktv_daugirdas(150, 50, 0, 2.5, 70) is None

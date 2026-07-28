"""Testes do parser de frequência do eMAR (puro, sem banco)."""
from __future__ import annotations

import datetime as dt

from app.domain.horarios import gerar_horarios

_INICIO = dt.datetime(2026, 7, 28, 8, 0, tzinfo=dt.timezone.utc)


def test_intervalo_8_8h_gera_3_doses_em_24h():
    horarios = gerar_horarios("8/8h", _INICIO)
    assert len(horarios) == 3
    assert horarios[1] - horarios[0] == dt.timedelta(hours=8)


def test_12_12h_e_6_6h():
    assert len(gerar_horarios("12/12h", _INICIO)) == 2
    assert len(gerar_horarios("6/6h", _INICIO)) == 4


def test_x_dia():
    assert len(gerar_horarios("1x/dia", _INICIO)) == 1
    assert len(gerar_horarios("3x/dia", _INICIO)) == 3


def test_dose_unica():
    assert gerar_horarios("dose única", _INICIO) == [_INICIO]


def test_frequencia_livre_nao_agenda():
    # Nunca "chutar" horário: padrão desconhecido → agendamento manual
    assert gerar_horarios("se dor", _INICIO) == []
    assert gerar_horarios(None, _INICIO) == []
    assert gerar_horarios("8/12h", _INICIO) == []  # intervalo inconsistente

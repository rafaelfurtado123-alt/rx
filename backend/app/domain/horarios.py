"""Geração de horários de administração (eMAR) a partir da frequência prescrita.

Padrões reconhecidos (case-insensitive):
  * "8/8h", "12/12h", "6/6h"  → a cada N horas
  * "1x/dia", "2x/dia", "3x/dia" → 24/N horas
  * "dose única", "agora" → uma dose no início

Frequências fora desses padrões retornam lista vazia — o agendamento passa a
ser manual (o sistema nunca "chuta" horário de medicação).
"""
from __future__ import annotations

import datetime as dt
import re

_RE_INTERVALO = re.compile(r"^(\d{1,2})/(\d{1,2})\s*h$", re.IGNORECASE)
_RE_X_DIA = re.compile(r"^(\d{1,2})\s*x/\s*dia$", re.IGNORECASE)
_UNICA = {"dose única", "dose unica", "agora", "imediato"}


def gerar_horarios(
    frequencia: str | None,
    inicio: dt.datetime,
    janela_horas: int = 24,
) -> list[dt.datetime]:
    """Horários previstos dentro da janela (padrão 24h) a partir de `inicio`."""
    if not frequencia:
        return []
    freq = frequencia.strip().lower()

    if freq in _UNICA:
        return [inicio]

    intervalo_h: float | None = None
    m = _RE_INTERVALO.match(freq)
    if m and m.group(1) == m.group(2):
        intervalo_h = float(m.group(1))
    else:
        m = _RE_X_DIA.match(freq)
        if m and int(m.group(1)) > 0:
            intervalo_h = 24 / int(m.group(1))

    if intervalo_h is None or intervalo_h <= 0:
        return []

    horarios: list[dt.datetime] = []
    t = inicio
    fim = inicio + dt.timedelta(hours=janela_horas)
    while t < fim:
        horarios.append(t)
        t += dt.timedelta(hours=intervalo_h)
    return horarios

"""Cálculos clínicos nefrológicos (puros, testáveis, sem dependências de framework).

Referências:
  * Kt/V single-pool — Daugirdas 2ª geração (JASN 1993).
  * URR — Urea Reduction Ratio.
  * nPCR — taxa de catabolismo proteico normalizada (estimativa a partir do Kt/V).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class AdequacaoHD:
    ktv: float | None
    urr: float | None
    npcr: float | None


def urr(ureia_pre: float, ureia_pos: float) -> float | None:
    """Urea Reduction Ratio (%) = (1 - pós/pré) * 100."""
    if ureia_pre <= 0:
        return None
    return round((1 - ureia_pos / ureia_pre) * 100, 1)


def ktv_daugirdas(
    ureia_pre: float,
    ureia_pos: float,
    duracao_horas: float,
    uf_litros: float,
    peso_pos_kg: float,
) -> float | None:
    """Kt/V single-pool (Daugirdas 2ª geração).

        Kt/V = -ln(R - 0.008*t) + (4 - 3.5*R) * UF/W

    onde R = ureia_pós/ureia_pré, t = horas, UF = ultrafiltração (L), W = peso pós (kg).
    """
    if ureia_pre <= 0 or peso_pos_kg <= 0 or duracao_horas <= 0:
        return None
    r = ureia_pos / ureia_pre
    inner = r - 0.008 * duracao_horas
    if inner <= 0:
        return None
    ktv = -math.log(inner) + (4 - 3.5 * r) * (uf_litros / peso_pos_kg)
    return round(ktv, 2)


def npcr_from_ktv(ureia_pre: float, ktv: float, frequencia_semanal: int = 3) -> float | None:
    """Estimativa de nPCR (g/kg/dia) a partir do Kt/V, para HD 3x/semana.

    Fórmula de Depner/Daugirdas simplificada para meio de semana (3x/sem):
        nPCR = ureia_pre / (36.3 + 5.48*Kt/V + 53.5/Kt/V) + 0.168
    """
    if ktv is None or ktv <= 0 or frequencia_semanal != 3:
        return None
    denom = 36.3 + 5.48 * ktv + 53.5 / ktv
    return round(ureia_pre / denom + 0.168, 2)


def adequacao(
    ureia_pre: float,
    ureia_pos: float,
    duracao_horas: float,
    uf_litros: float,
    peso_pos_kg: float,
    frequencia_semanal: int = 3,
) -> AdequacaoHD:
    """Calcula Kt/V, URR e nPCR de uma sessão de HD."""
    k = ktv_daugirdas(ureia_pre, ureia_pos, duracao_horas, uf_litros, peso_pos_kg)
    return AdequacaoHD(
        ktv=k,
        urr=urr(ureia_pre, ureia_pos),
        npcr=npcr_from_ktv(ureia_pre, k, frequencia_semanal) if k else None,
    )


def volume_uf(peso_atual_kg: float, peso_seco_kg: float) -> float:
    """Volume a ultrafiltrar (L) = peso atual − peso seco (mínimo 0)."""
    return round(max(peso_atual_kg - peso_seco_kg, 0.0), 2)

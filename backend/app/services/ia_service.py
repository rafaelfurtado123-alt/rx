"""Camada de IA auxiliar (sumarização de evolução).

Princípios (guardrails):
  * A IA NUNCA decide — apenas sugere. Toda saída é RASCUNHO e exige revisão/assinatura.
  * PHI minimizado: apenas o conteúdo clínico necessário é processado.
  * Determinístico por padrão (sem provedor externo configurado), garantindo que o
    sistema funcione offline e nunca "invente" dados. Um provedor LLM pode ser
    plugado em `summarize_soap` mantendo os mesmos guardrails.
"""
from __future__ import annotations

from ..schemas.prontuario import ResumoIARequest


def summarize_soap(data: ResumoIARequest) -> str:
    """Gera um resumo estruturado a partir dos campos SOAP preenchidos.

    Implementação determinística: compõe uma síntese ancorada exclusivamente no que
    foi digitado (não acrescenta valores). Substituível por um LLM sem alterar a API.
    """
    partes: list[str] = []
    if data.subjetivo:
        partes.append(f"Paciente refere {_frase(data.subjetivo)}")
    if data.objetivo:
        partes.append(f"Ao exame/objetivo: {_frase(data.objetivo)}")
    if data.avaliacao:
        partes.append(f"Avaliação: {_frase(data.avaliacao)}")
    if data.plano:
        partes.append(f"Conduta: {_frase(data.plano)}")
    if not partes and data.texto_livre:
        partes.append(_frase(data.texto_livre))

    if not partes:
        return "Sem conteúdo suficiente para sumarizar."
    return " ".join(partes)


def _frase(texto: str) -> str:
    t = " ".join(texto.strip().split())
    if not t:
        return ""
    t = t[0].lower() + t[1:]
    return t if t.endswith(".") else t + "."

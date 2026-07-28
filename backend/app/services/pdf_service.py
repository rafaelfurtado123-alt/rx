"""Geração de PDF do LME e do Termo de Esclarecimento (TER).

Gera on-demand (bytes) no formato do Laudo para Solicitação, Avaliação e
Autorização de Medicamentos do Componente Especializado (CEAF). Layout A4
sóbrio e imprimível; assinatura ICP-Brasil entra como evolução (PAdES).
"""
from __future__ import annotations

import datetime as dt
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..models.core import Paciente, Profissional, Unidade
from ..schemas.lme import LaudoOut

_AZUL = colors.HexColor("#0E7C86")


def _styles():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", parent=base["Title"], fontSize=14,
                                 textColor=_AZUL, spaceAfter=2),
        "sub": ParagraphStyle("sub", parent=base["Normal"], fontSize=9,
                              textColor=colors.grey, spaceAfter=8),
        "secao": ParagraphStyle("secao", parent=base["Heading4"], fontSize=10,
                                textColor=_AZUL, spaceBefore=10, spaceAfter=4),
        "corpo": ParagraphStyle("corpo", parent=base["Normal"], fontSize=9.5,
                                leading=13),
    }


def _tabela(dados: list[list[str]], larguras: list[float]) -> Table:
    t = Table(dados, colWidths=larguras)
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#DDDDDD")),
    ]))
    return t


def gerar_pdf_lme(
    laudo: LaudoOut,
    paciente: Paciente,
    medico: Profissional,
    unidade: Unidade,
) -> bytes:
    """PDF oficial do LME."""
    buf = BytesIO()
    # invariant=1 → CreationDate/ID determinísticos: o MESMO laudo gera os
    # MESMOS bytes, essencial para a assinatura destacada ser verificável.
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm,
                            bottomMargin=18 * mm, leftMargin=16 * mm,
                            rightMargin=16 * mm, title=f"LME {laudo.id}",
                            invariant=1)
    s = _styles()
    story: list = []

    story.append(Paragraph("LAUDO DE SOLICITAÇÃO DE MEDICAMENTO — LME", s["titulo"]))
    story.append(Paragraph(
        "Componente Especializado da Assistência Farmacêutica (CEAF)", s["sub"]))
    story.append(HRFlowable(width="100%", color=_AZUL, thickness=1))

    story.append(Paragraph("1. Estabelecimento solicitante", s["secao"]))
    story.append(_tabela([
        ["Estabelecimento", unidade.nome],
        ["CNES", unidade.cnes or "—"],
    ], [40 * mm, 130 * mm]))

    nasc = paciente.data_nascimento.strftime("%d/%m/%Y") \
        if paciente.data_nascimento else "—"
    story.append(Paragraph("2. Paciente", s["secao"]))
    story.append(_tabela([
        ["Nome", paciente.nome],
        ["CNS", paciente.cns or "—"],
        ["CPF", paciente.cpf or "—"],
        ["Nascimento", nasc],
    ], [40 * mm, 130 * mm]))

    story.append(Paragraph("3. Medicamento solicitado", s["secao"]))
    story.append(_tabela([
        ["Medicamento", laudo.medicamento],
        ["Posologia", laudo.posologia or "—"],
        ["Quantidade/mês", f"{laudo.quantidade_mes or '—'}"],
        ["CID-10 principal", laudo.cid_principal or "—"],
        ["CID-10 secundários", ", ".join(laudo.cids_secundarios) or "—"],
        ["Protocolo (PCDT)",
         f"{laudo.pcdt_nome or '—'} — versão {laudo.pcdt_versao or '—'}"],
    ], [40 * mm, 130 * mm]))

    story.append(Paragraph("4. Anamnese", s["secao"]))
    story.append(Paragraph(laudo.anamnese or "—", s["corpo"]))
    story.append(Paragraph("5. Justificativa clínica", s["secao"]))
    story.append(Paragraph(laudo.justificativa or "—", s["corpo"]))

    story.append(Paragraph("6. Exames comprobatórios", s["secao"]))
    linhas = [["Exame", "Resultado", "Data", "Situação"]]
    for e in laudo.exames:
        data = e.data_coleta.strftime("%d/%m/%Y") if e.data_coleta else "—"
        valor = f"{e.valor} {e.unidade or ''}".strip() if e.valor is not None else "—"
        linhas.append([e.nome, valor, data, e.situacao])
    t = Table(linhas, colWidths=[62 * mm, 40 * mm, 30 * mm, 38 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF3F5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), _AZUL),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    emitido = laudo.emitido_em.strftime("%d/%m/%Y") if laudo.emitido_em else "—"
    validade = laudo.valido_ate.strftime("%d/%m/%Y") if laudo.valido_ate else "—"
    story.append(Paragraph("7. Emissão e validade", s["secao"]))
    story.append(_tabela([
        ["Situação", laudo.status.upper()],
        ["Emitido em", emitido],
        ["Válido até", f"{validade}  (validade de 90 dias)"],
    ], [40 * mm, 130 * mm]))

    conselho = f"{medico.conselho_tipo or 'CRM'} {medico.conselho_num or ''}" \
               f"/{medico.conselho_uf or ''}"
    story.append(Spacer(1, 16 * mm))
    story.append(HRFlowable(width="60%", color=colors.grey, thickness=0.5))
    story.append(Paragraph(f"{medico.nome} — {conselho}", s["corpo"]))
    # Rodapé sem timestamp de geração (o documento precisa ser determinístico
    # para a assinatura destacada); a data oficial é a de emissão.
    story.append(Paragraph(
        f"Documento gerado eletronicamente pelo sistema Néfron. "
        f"Emissão: {emitido}. Identificador: {laudo.id}", s["sub"]))

    doc.build(story)
    return buf.getvalue()


def gerar_pdf_receita(
    paciente: Paciente,
    medico: Profissional,
    unidade: Unidade,
    itens: list[dict],
    tipo: str,
    data_emissao: dt.datetime | None,
) -> bytes:
    """PDF do receituário — 'simples' ou 'controle_especial' (Portaria 344/98).

    O receituário de controle especial sai em DUAS vias na mesma folha
    (1ª via: farmácia · 2ª via: paciente), com o box de identificação do
    emitente exigido pela norma. Determinístico (invariant) para permitir
    assinatura destacada verificável.
    """
    buf = BytesIO()
    titulo = ("RECEITUÁRIO DE CONTROLE ESPECIAL" if tipo == "controle_especial"
              else "RECEITUÁRIO")
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=14 * mm,
                            bottomMargin=14 * mm, leftMargin=16 * mm,
                            rightMargin=16 * mm, title=titulo, invariant=1)
    s = _styles()
    emissao = data_emissao.strftime("%d/%m/%Y") if data_emissao else "—"
    conselho = f"{medico.conselho_tipo or 'CRM'} {medico.conselho_num or ''}" \
               f"/{medico.conselho_uf or ''}"

    def _via(rotulo_via: str | None) -> list:
        bloco: list = [Paragraph(titulo, s["titulo"])]
        if rotulo_via:
            bloco.append(Paragraph(rotulo_via, s["sub"]))
        bloco.append(HRFlowable(width="100%", color=_AZUL, thickness=1))
        # Box de identificação do emitente (exigido no controle especial)
        bloco.append(Paragraph("Identificação do emitente", s["secao"]))
        bloco.append(_tabela([
            ["Estabelecimento", f"{unidade.nome} — CNES {unidade.cnes or '—'}"],
            ["Profissional", f"{medico.nome} — {conselho}"],
        ], [40 * mm, 130 * mm]))
        bloco.append(Paragraph("Paciente", s["secao"]))
        bloco.append(_tabela([
            ["Nome", paciente.nome],
            ["CNS", paciente.cns or "—"],
        ], [40 * mm, 130 * mm]))
        bloco.append(Paragraph("Prescrição", s["secao"]))
        for i, item in enumerate(itens, start=1):
            partes = [item.get("nome", "—")]
            if item.get("apresentacao"):
                partes.append(item["apresentacao"])
            if item.get("dose"):
                partes.append(f"{item['dose']} {item.get('unidade_dose') or ''}".strip())
            if item.get("via"):
                partes.append(item["via"])
            if item.get("frequencia"):
                partes.append(item["frequencia"])
            if item.get("duracao"):
                partes.append(item["duracao"])
            sufixo = "  [CONTROLADO]" if item.get("controlado") else ""
            bloco.append(Paragraph(
                f"{i}. " + " — ".join(str(p) for p in partes) + sufixo, s["corpo"]))
        bloco.append(Spacer(1, 8 * mm))
        bloco.append(Paragraph(f"Data de emissão: {emissao}", s["corpo"]))
        bloco.append(Spacer(1, 10 * mm))
        bloco.append(HRFlowable(width="60%", color=colors.grey, thickness=0.5))
        bloco.append(Paragraph(f"{medico.nome} — {conselho}", s["sub"]))
        return bloco

    story: list = []
    if tipo == "controle_especial":
        story += _via("1ª via — farmácia")
        story.append(Spacer(1, 6 * mm))
        story.append(HRFlowable(width="100%", color=colors.grey, thickness=0.5,
                                dash=(2, 2)))
        story.append(Spacer(1, 6 * mm))
        story += _via("2ª via — paciente")
    else:
        story += _via(None)

    doc.build(story)
    return buf.getvalue()


def gerar_pdf_termo(texto: str, paciente: Paciente, medicamento: str,
                    aceite_por: str | None, aceite_em: dt.datetime | None) -> bytes:
    """PDF do Termo de Esclarecimento e Responsabilidade."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm,
                            bottomMargin=18 * mm, leftMargin=16 * mm,
                            rightMargin=16 * mm, title="TER", invariant=1)
    s = _styles()
    story: list = [
        Paragraph("TERMO DE ESCLARECIMENTO E RESPONSABILIDADE", s["titulo"]),
        Paragraph(f"Paciente: {paciente.nome} — Medicamento: {medicamento}", s["sub"]),
        HRFlowable(width="100%", color=_AZUL, thickness=1),
        Spacer(1, 6 * mm),
    ]
    for par in texto.split("\n\n"):
        story.append(Paragraph(par.replace("\n", "<br/>"), s["corpo"]))
        story.append(Spacer(1, 3 * mm))

    story.append(Spacer(1, 14 * mm))
    if aceite_por and aceite_em:
        story.append(Paragraph(
            f"Aceito por {aceite_por} em {aceite_em.strftime('%d/%m/%Y %H:%M')} UTC.",
            s["corpo"]))
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="60%", color=colors.grey, thickness=0.5))
    story.append(Paragraph("Assinatura do paciente ou responsável", s["sub"]))

    doc.build(story)
    return buf.getvalue()

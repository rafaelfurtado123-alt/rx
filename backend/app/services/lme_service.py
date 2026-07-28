"""LME Inteligente — motor de regras PCDT.

Fluxo (ver docs/03-fluxos-principais.md §3):
  1. Médico escolhe o medicamento CEAF → sistema localiza o PCDT vigente
     (`ref.pcdt.regras_json.medicamentos`).
  2. Autopreenche: dados do paciente/médico, CID-10 (N18.x pelo estágio/TRS +
     secundários do protocolo) e os exames MAIS RECENTES exigidos.
  3. Valida exames obrigatórios: presente | ausente | vencido (mais antigo que
     `periodicidade_exames_dias`). Pendência ⇒ NÃO emite (fica rascunho).
  4. Gera anamnese + justificativa ancoradas EXCLUSIVAMENTE nos dados reais
     (guardrail: nunca inventa valores; cita exame, valor e data).
  5. Assinatura emite o laudo: status vigente, validade de 90 dias, TER aceito.
  6. Renovação em 1 clique: clona o laudo, reavalia os exames e encadeia
     `laudo_anterior_id`; o anterior passa a `renovado`.
"""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.clinico import ExameResultado, RefExame
from ..models.core import Paciente
from ..models.hd import RefMedicamento
from ..models.lme import ExameVinculado, Laudo, LaudoItem, RefPcdt, Termo
from ..schemas.auth import CurrentUser
from ..schemas.lme import ExameChecagem, LaudoOut, LmeGerarRequest

VALIDADE_DIAS = 90
TERMO_VERSAO = "TER-2024.1"


# ------------------------- Motor PCDT -------------------------
async def _pcdt_para_medicamento(
    session: AsyncSession, med: RefMedicamento
) -> RefPcdt | None:
    """Localiza o PCDT vigente cujo protocolo inclui o princípio ativo."""
    hoje = dt.date.today()
    pcdts = await session.scalars(select(RefPcdt).order_by(RefPcdt.vigencia_ini.desc()))
    for pcdt in pcdts:
        if pcdt.vigencia_ini > hoje:
            continue
        if pcdt.vigencia_fim is not None and pcdt.vigencia_fim < hoje:
            continue
        medicamentos = pcdt.regras_json.get("medicamentos", [])
        if med.principio_ativo in medicamentos:
            return pcdt
    return None


async def _checar_exames(
    session: AsyncSession, paciente_id: str, regras: dict
) -> list[ExameChecagem]:
    """Para cada exame obrigatório do PCDT, busca o resultado mais recente e
    classifica: presente | ausente | vencido (fora da periodicidade)."""
    periodicidade = int(regras.get("periodicidade_exames_dias", VALIDADE_DIAS))
    limite = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=periodicidade)
    checagens: list[ExameChecagem] = []

    for codigo in regras.get("exames_obrigatorios", []):
        ref = await session.scalar(select(RefExame).where(RefExame.codigo == codigo))
        if ref is None:
            checagens.append(ExameChecagem(
                codigo=codigo, nome=codigo, situacao="ausente"))
            continue
        resultado = await session.scalar(
            select(ExameResultado)
            .where(ExameResultado.paciente_id == paciente_id,
                   ExameResultado.exame_id == ref.id,
                   ExameResultado.valor.is_not(None))
            .order_by(ExameResultado.data_coleta.desc())
            .limit(1)
        )
        if resultado is None:
            situacao = "ausente"
        elif resultado.data_coleta < limite:
            situacao = "vencido"
        else:
            situacao = "presente"
        checagens.append(ExameChecagem(
            codigo=codigo, nome=ref.nome, situacao=situacao,
            valor=float(resultado.valor) if resultado is not None else None,
            unidade=ref.unidade,
            data_coleta=resultado.data_coleta if resultado is not None else None,
        ))
    return checagens


def _cid_automatico(paciente: Paciente, regras: dict) -> tuple[str | None, list[str]]:
    """CID principal pelo estágio da DRC (N18.6 se em TRS) + secundários do PCDT."""
    aceitos: list[str] = regras.get("cids_aceitos", [])
    em_trs = paciente.inicio_trs is not None or paciente.turno_dialise is not None

    principal: str | None = None
    if em_trs and "N18.6" in aceitos:
        principal = "N18.6"
    elif paciente.estagio_drc is not None:
        candidato = f"N18.{paciente.estagio_drc}"
        if candidato in aceitos:
            principal = candidato
    if principal is None and aceitos:
        # fallback: primeiro N18.x aceito
        principal = next((c for c in aceitos if c.startswith("N18")), aceitos[0])

    secundarios = [c for c in aceitos if not c.startswith("N18") and c != principal]
    return principal, secundarios


def _fmt_exame(e: ExameChecagem) -> str:
    data = e.data_coleta.strftime("%d/%m/%Y") if e.data_coleta else "s/d"
    return f"{e.nome} {e.valor} {e.unidade or ''} ({data})".replace("  ", " ").strip()


def _gerar_anamnese(paciente: Paciente, exames: list[ExameChecagem]) -> str:
    """Anamnese determinística ancorada nos dados reais do prontuário."""
    partes: list[str] = []
    idade = None
    if paciente.data_nascimento:
        hoje = dt.date.today()
        idade = hoje.year - paciente.data_nascimento.year - (
            (hoje.month, hoje.day)
            < (paciente.data_nascimento.month, paciente.data_nascimento.day))
    quem = f"Paciente{f', {idade} anos,' if idade else ''}"
    drc = f"portador(a) de doença renal crônica estágio {paciente.estagio_drc}" \
        if paciente.estagio_drc else "portador(a) de doença renal crônica"
    if paciente.etiologia_drc:
        drc += f" secundária a {paciente.etiologia_drc.lower()}"
    partes.append(f"{quem} {drc}.")
    if paciente.inicio_trs:
        partes.append(
            "Em terapia renal substitutiva (hemodiálise) desde "
            f"{paciente.inicio_trs.strftime('%d/%m/%Y')}.")
    presentes = [e for e in exames if e.situacao == "presente" and e.valor is not None]
    if presentes:
        partes.append("Exames recentes: " + "; ".join(_fmt_exame(e) for e in presentes) + ".")
    return " ".join(partes)


def _gerar_justificativa(
    pcdt: RefPcdt, med: RefMedicamento, exames: list[ExameChecagem]
) -> str:
    """Justificativa alinhada ao PCDT, citando metas e os valores reais."""
    metas: dict = pcdt.regras_json.get("metas", {})
    frases: list[str] = [
        f"Solicito {med.principio_ativo} ({med.apresentacao}) conforme o "
        f"PCDT '{pcdt.nome}' (versão {pcdt.versao})."
    ]
    fora_de_meta: list[str] = []
    for e in exames:
        if e.situacao != "presente" or e.valor is None:
            continue
        if e.codigo == "HB" and "hb_min" in metas and e.valor < float(metas["hb_min"]):
            fora_de_meta.append(
                f"hemoglobina {e.valor} g/dL abaixo do alvo mínimo de {metas['hb_min']} g/dL")
        if e.codigo == "TSAT" and "tsat_min" in metas and e.valor < float(metas["tsat_min"]):
            fora_de_meta.append(
                f"saturação de transferrina {e.valor}% abaixo de {metas['tsat_min']}%")
        if e.codigo == "FERR" and "ferritina_min" in metas \
                and e.valor < float(metas["ferritina_min"]):
            fora_de_meta.append(
                f"ferritina {e.valor} ng/mL abaixo de {metas['ferritina_min']} ng/mL")
        if e.codigo == "P" and "p_max" in metas and e.valor > float(metas["p_max"]):
            fora_de_meta.append(
                f"fósforo {e.valor} mg/dL acima do alvo máximo de {metas['p_max']} mg/dL")
        if e.codigo == "PTH" and "pth_dialise_max" in metas \
                and e.valor > float(metas["pth_dialise_max"]):
            fora_de_meta.append(
                f"PTH {e.valor} pg/mL acima do alvo de {metas['pth_dialise_max']} pg/mL")
    if fora_de_meta:
        frases.append("Paciente apresenta " + "; ".join(fora_de_meta) +
                      ", preenchendo critério clínico do protocolo.")
    else:
        frases.append("Uso em manutenção terapêutica dentro dos critérios do protocolo.")
    frases.append("Exames comprobatórios anexos conforme exigência do protocolo.")
    return " ".join(frases)


def _texto_termo(med: RefMedicamento) -> str:
    """Texto do Termo de Esclarecimento e Responsabilidade (modelo CEAF)."""
    return (
        "TERMO DE ESCLARECIMENTO E RESPONSABILIDADE\n\n"
        f"Medicamento: {med.principio_ativo} — {med.apresentacao}\n\n"
        "Declaro que fui esclarecido(a) sobre os benefícios, riscos, contraindicações "
        "e principais efeitos adversos relacionados ao uso do medicamento acima, "
        "conforme o Protocolo Clínico e Diretrizes Terapêuticas do Ministério da Saúde. "
        "Comprometo-me a utilizá-lo conforme a prescrição médica e a comunicar "
        "imediatamente qualquer reação adversa. Estou ciente de que o fornecimento "
        "depende da renovação periódica desta solicitação e da realização dos exames "
        "de monitorização exigidos pelo protocolo."
    )


# ------------------------- Casos de uso -------------------------
async def gerar(
    session: AsyncSession, paciente_id: str, body: LmeGerarRequest, user: CurrentUser
) -> LaudoOut:
    """Gera o LME (rascunho) com autopreenchimento e checagem de exames."""
    paciente = await session.get(Paciente, paciente_id)
    if paciente is None or paciente.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "paciente não encontrado")
    med = await session.get(RefMedicamento, body.medicamento_id)
    if med is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "medicamento não catalogado")
    if not med.requer_lme:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "medicamento não exige LME (não é do CEAF)")

    pcdt = await _pcdt_para_medicamento(session, med)
    if pcdt is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "nenhum PCDT vigente cobre este medicamento")

    exames = await _checar_exames(session, paciente_id, pcdt.regras_json)
    cid_auto, secundarios = _cid_automatico(paciente, pcdt.regras_json)
    cid = body.cid_principal or cid_auto

    pendencias: list[str] = []
    for e in exames:
        if e.obrigatorio and e.situacao != "presente":
            rotulo = "ausente" if e.situacao == "ausente" else "vencido (>90 dias)"
            pendencias.append(f"Exame obrigatório {e.nome} ({e.codigo}): {rotulo}")
    if cid is None:
        pendencias.append("CID-10 principal não determinado")
    elif cid not in pcdt.regras_json.get("cids_aceitos", [cid]):
        pendencias.append(f"CID {cid} fora dos aceitos pelo PCDT")

    anamnese = body.anamnese or _gerar_anamnese(paciente, exames)
    justificativa = body.justificativa or _gerar_justificativa(pcdt, med, exames)

    laudo = Laudo(
        paciente_id=paciente_id, medico_id=user.profissional_id,
        unidade_id=user.unidade_id, pcdt_id=pcdt.id,
        cid_principal=cid, cids_secundarios=secundarios,
        anamnese=anamnese, justificativa=justificativa,
        status="rascunho",
        ia_metadados={"gerador": "pcdt-engine-v1",
                      "exames_citados": [e.codigo for e in exames
                                         if e.situacao == "presente"]},
    )
    session.add(laudo)
    await session.flush()

    session.add(LaudoItem(
        laudo_id=laudo.id, medicamento_id=med.id, cid=cid,
        posologia=body.posologia, quantidade_mes=body.quantidade_mes,
        unidade=med.unidade_dose,
    ))
    for e in exames:
        ref = await session.scalar(select(RefExame).where(RefExame.codigo == e.codigo))
        resultado_id = None
        if e.situacao == "presente" and ref is not None:
            resultado = await session.scalar(
                select(ExameResultado)
                .where(ExameResultado.paciente_id == paciente_id,
                       ExameResultado.exame_id == ref.id)
                .order_by(ExameResultado.data_coleta.desc()).limit(1))
            resultado_id = resultado.id if resultado else None
        if ref is not None:
            session.add(ExameVinculado(
                laudo_id=laudo.id, exame_id=ref.id,
                exame_resultado_id=resultado_id, situacao=e.situacao))

    session.add(Termo(laudo_id=laudo.id, versao=TERMO_VERSAO, texto=_texto_termo(med)))
    await session.commit()
    return await _laudo_out(session, laudo, exames=exames, pendencias=pendencias)


async def assinar(
    session: AsyncSession, laudo_id: str, aceite_por: str | None, user: CurrentUser
) -> LaudoOut:
    """Assina/emite o LME: exige zero pendências. Validade = 90 dias."""
    laudo = await _get_laudo(session, laudo_id)
    if laudo.status not in ("rascunho", "emitido"):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"laudo em status '{laudo.status}' não pode ser assinado")

    pcdt = await session.get(RefPcdt, laudo.pcdt_id) if laudo.pcdt_id else None
    exames = await _checar_exames(
        session, str(laudo.paciente_id), pcdt.regras_json if pcdt else {})
    pendencias = [f"Exame obrigatório {e.nome} ({e.codigo}): {e.situacao}"
                  for e in exames if e.obrigatorio and e.situacao != "presente"]
    if pendencias:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "não é possível emitir com pendências: " + "; ".join(pendencias))

    agora = dt.datetime.now(dt.timezone.utc)
    laudo.status = "vigente"
    laudo.emitido_em = agora
    laudo.valido_ate = agora + dt.timedelta(days=VALIDADE_DIAS)

    termo = await session.scalar(select(Termo).where(Termo.laudo_id == laudo.id))
    if termo is not None and aceite_por:
        termo.aceite_em = agora
        termo.aceite_por = aceite_por

    await session.commit()
    return await _laudo_out(session, laudo, exames=exames, pendencias=[])


async def renovar(session: AsyncSession, laudo_id: str, user: CurrentUser) -> LaudoOut:
    """Renovação em 1 clique: clona o laudo, reavalia exames, encadeia a origem."""
    origem = await _get_laudo(session, laudo_id)
    if origem.status not in ("vigente", "vencido"):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "apenas laudos vigentes ou vencidos podem ser renovados")

    item = await session.scalar(
        select(LaudoItem).where(LaudoItem.laudo_id == origem.id))
    if item is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "laudo de origem sem item de medicamento")

    novo = await gerar(
        session, str(origem.paciente_id),
        LmeGerarRequest(
            medicamento_id=item.medicamento_id,
            posologia=item.posologia,
            quantidade_mes=float(item.quantidade_mes)
            if item.quantidade_mes is not None else None,
            cid_principal=origem.cid_principal,
        ),
        user,
    )
    # Encadeia e marca a origem como renovada
    novo_row = await session.get(Laudo, novo.id)
    novo_row.laudo_anterior_id = origem.id
    origem.status = "renovado"
    await session.commit()
    novo.laudo_anterior_id = origem.id
    return novo


async def listar(session: AsyncSession, paciente_id: str) -> list[LaudoOut]:
    """Histórico de LMEs do paciente, marcando vencidos na leitura."""
    laudos = await session.scalars(
        select(Laudo).where(Laudo.paciente_id == paciente_id)
        .order_by(Laudo.id.desc()))
    agora = dt.datetime.now(dt.timezone.utc)
    out: list[LaudoOut] = []
    for laudo in laudos:
        # Vencimento automático na leitura (job periódico cuida em lote)
        if (laudo.status == "vigente" and laudo.valido_ate is not None
                and laudo.valido_ate < agora):
            laudo.status = "vencido"
        out.append(await _laudo_out(session, laudo))
    await session.commit()
    return out


async def obter(session: AsyncSession, laudo_id: str) -> LaudoOut:
    laudo = await _get_laudo(session, laudo_id)
    return await _laudo_out(session, laudo)


# ------------------------- helpers -------------------------
async def _get_laudo(session: AsyncSession, laudo_id: str) -> Laudo:
    laudo = await session.get(Laudo, laudo_id)
    if laudo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "laudo não encontrado")
    return laudo


async def _laudo_out(
    session: AsyncSession, laudo: Laudo,
    exames: list[ExameChecagem] | None = None,
    pendencias: list[str] | None = None,
) -> LaudoOut:
    item = await session.scalar(select(LaudoItem).where(LaudoItem.laudo_id == laudo.id))
    med = await session.get(RefMedicamento, item.medicamento_id) if item else None
    pcdt = await session.get(RefPcdt, laudo.pcdt_id) if laudo.pcdt_id else None
    termo = await session.scalar(select(Termo).where(Termo.laudo_id == laudo.id))

    if exames is None:
        exames = await _checar_exames(
            session, str(laudo.paciente_id), pcdt.regras_json if pcdt else {})
    if pendencias is None:
        pendencias = [f"Exame obrigatório {e.nome} ({e.codigo}): {e.situacao}"
                      for e in exames if e.obrigatorio and e.situacao != "presente"]

    dias = None
    if laudo.valido_ate is not None:
        dias = (laudo.valido_ate - dt.datetime.now(dt.timezone.utc)).days

    return LaudoOut(
        id=laudo.id, status=laudo.status,
        medicamento=med.principio_ativo if med else "?",
        posologia=item.posologia if item else None,
        quantidade_mes=float(item.quantidade_mes)
        if item and item.quantidade_mes is not None else None,
        pcdt_nome=pcdt.nome if pcdt else None,
        pcdt_versao=pcdt.versao if pcdt else None,
        cid_principal=laudo.cid_principal,
        cids_secundarios=laudo.cids_secundarios or [],
        anamnese=laudo.anamnese, justificativa=laudo.justificativa,
        exames=exames, pendencias=pendencias,
        emitido_em=laudo.emitido_em, valido_ate=laudo.valido_ate,
        dias_restantes=dias, laudo_anterior_id=laudo.laudo_anterior_id,
        termo_versao=termo.versao if termo else None,
    )

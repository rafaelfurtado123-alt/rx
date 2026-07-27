# Néfron — Wireframes de Alta Fidelidade (texto)

Descrição textual de alta fidelidade das telas-chave (Etapa 2). Notação:
`[...]` botão · `〔...〕` card de vidro · `▸` navegação · `◉` seleção ativa · `▲/▼` tendência.
Layout descrito para **tablet retrato** (referência); adapta para telefone (1 coluna) e web (2–3 colunas).

---

## 1. Login + 2FA

```
┌───────────────────────────── fundo em gradiente escuro ─────────────────────────────┐
│                                                                                       │
│                              néfron·                                                   │
│                    Prontuário Nefrológico                                              │
│                                                                                       │
│        〔 GlassCard central                                                        〕  │
│        〔  E-mail / CRM        [__________________________]                        〕  │
│        〔  Senha               [__________________________] 👁                     〕  │
│        〔                                                                          〕  │
│        〔                    [  Entrar  ]  (primary, largura total)                〕  │
│        〔  ─────────────  ou  ─────────────                                        〕  │
│        〔  [ Entrar com certificado ICP-Brasil ]                                   〕  │
│                                                                                       │
│        Ao continuar, você concorda com o registro de acesso (LGPD).                    │
└───────────────────────────────────────────────────────────────────────────────────┘

→ após senha: tela 2FA (TOTP)
〔  Código de verificação   [ _ _ _  _ _ _ ]   ← 6 dígitos, teclado numérico grande 〕
〔  [ Verificar ]   Reenviar em 0:30                                                  〕

→ se múltiplos vínculos: seletor
〔 Selecione a unidade / perfil 〕
  ◉ Clínica Néfron — Médico
  ○ Hospital X — Médico
```

---

## 2. Dashboard do Médico

```
┌ TopBar: néfron·  ·  Clínica Néfron ▾  ·  🔍 busca global  ·  🔔3  ·  avatar ▾ ┐
│                                                                              │
│  Bom dia, Dra. Ana ·  Sexta, 27/07                                           │
│                                                                              │
│  〔 ALERTAS PROATIVOS ─────────────────────────────── [ver todos] 〕         │
│  ┃ 🔴 3 pacientes com Hb < 10 (meta anemia)                                  │
│  ┃ 🟠 2 LMEs vencem em 7 dias                                                 │
│  ┃ 🟠 1 PTH acima da meta (DMO-DRC)                                           │
│                                                                              │
│  ┌── 4 VitalTiles em grade 2×2 (resumo do dia) ──────────────────────────┐  │
│  │ 〔 Pacientes hoje  18 〕   〔 A assinar  5 〕                            │  │
│  │ 〔 LMEs a vencer  2  〕   〔 Intercorrências 24h  1 🔴 〕                │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  〔 MEUS PACIENTES (turno da manhã) ──────────── [+ Novo] 〕                 │
│  ┃ ◉ Maria S.  · N18.6 · HD 2ª/4ª/6ª · Hb 9.4 🔴 ▼ · Kt/V 1.3 ✓           │
│  ┃   João P.   · N18.5 · Hb 11.2 ✓ · PTH 720 🟠 ▲ · LME vence D-7          │
│  ┃   Ana L.    · N18.6 · P 6.1 🟠 · próx. consulta 02/08                    │
│                                                                              │
│  [ FAB contextual: + Evolução / + Prescrição / + LME ]  (2 cliques)          │
└──────────────────────────────────────────────────────────────────────────┘
Nav inferior (mobile): Início · Pacientes · Agenda · Sala HD · Mais
```

---

## 3. Prontuário do Paciente — Timeline unificada

```
┌ ← Maria Silva · 58a · ♀ · CNS 700… · N18.6 · FAV braço E ·  [⋮] ┐
│  chips: 🩸 O+  ·  💉 Hep B ✓  ·  Alergia: Dipirona 🔴  ·  Peso seco 70 kg  │
│                                                                          │
│  Abas:  ◉ Linha do tempo | Evolução | Exames | Prescrições | HD | LME     │
│                                                                          │
│  〔 LINHA DO TEMPO (filtro: Todos ▾) ────────────────────────────────〕   │
│  │ hoje 07:10  🩺 Sessão de HD  — Kt/V 1.3 · UF 2.4L · sem intercorr. ▸ │
│  │ hoje 06:55  🧪 Exames  — Hb 9.4 🔴 ▼ · Ferritina 180 🟠            ▸ │
│  │ 25/07       📝 Evolução médica (Dra. Ana) — ajuste EPO             ▸ │
│  │ 24/07       💊 Prescrição HD atualizada                            ▸ │
│  │ 20/07       📄 LME Alfaepoetina emitido — válido até 18/10         ▸ │
│                                                                          │
│  [ FAB: + Evolução · + Prescrição · + LME · + Exame ]                     │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.1 Aba Exames (gráficos de tendência)

```
〔 Hemoglobina (g/dL) ─── últimos 12 meses ───────────────〕
   faixa-meta 10–12 sombreada (verde);  linha da série;
   ponto atual 9.4 marcado em 🔴 abaixo da faixa;  ▼ -0.8 vs anterior
   [ 3m | 6m | 12m | tudo ]     [ comparar: Ferritina ▾ ]

〔 PTH · Ca · P (DMO-DRC) 〕  multi-série · faixas-meta · alertas
〔 Kt/V · nPCR (adequação) 〕  meta 1.2 · média móvel
```

---

## 4. Evolução SOAP (multiprofissional)

```
┌ ← Nova evolução · Maria Silva · categoria: Médica ▾ ┐
│  〔 S — Subjetivo   [ texto…                       ] 〕                │
│  〔 O — Objetivo    [ texto…  · inserir sinais/exames ⊕ ]           〕 │
│  〔 A — Avaliação   [ texto…                       ] 〕                │
│  〔 P — Plano       [ texto…                       ] 〕                │
│  [ ✨ Sumarizar com IA ]  → gera rascunho (revisar antes de assinar)  │
│                                                                       │
│  Texto livre  [ ………………………………………………………… ]                              │
│                                                                       │
│  [ Salvar rascunho ]              [ Assinar e fechar ]  (step-up)      │
└───────────────────────────────────────────────────────────────────┘
Tela única mostra à direita (tablet) as evoluções recentes de todos os
profissionais, filtráveis por categoria (médica/enf/nutri/…).
```

---

## 5. Prescrição de Hemodiálise (nível Tasy)

```
┌ ← Prescrição de HD · Maria Silva ┐
│  〔 Modalidade   ◉ IHD  ○ SLED  ○ HDF online  ○ CVVHDF 〕                │
│  〔 Duração [240] min   ·  Frequência 2ª/4ª/6ª ▾              〕         │
│  〔 Qb [ 350 ] mL/min      Qd [ 500 ] mL/min                 〕         │
│  〔 Dialisador [ FX80 ▾ ]   Reúso [ 3 ]                       〕         │
│  〔 Acesso [ FAV braço E ▾ ]   Ponto de punção [ … ]          〕         │
│  〔 Peso atual [72.5] kg   Peso seco [70.0] kg                〕         │
│  〔 ► UF prescrita [ 2.5 ] L    UF máxima [ 3.0 ] L           〕         │
│  〔    Volume calculado: 2.5 L  (peso atual − peso seco)  auto 〕        │
│  〔 Perfil de sódio  ◉ Ramp 145→138   Bicarbonato [ 32 ]      〕         │
│  〔 Heparinização  ◉ Sistêmica  bolus [ ] UI  manut. [ ] UI/h 〕         │
│  〔 Soluções/medicações na sessão  [ + adicionar ]           〕          │
│                                                                        │
│  [ Salvar rascunho ]                     [ Assinar prescrição ]         │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.1 Módulo de Sessão (sala de HD, tablet)

```
〔 Recepção 〕 Peso pré [72.4] · PA [140/85] · FC [78] · Tª [36.2] · queixas […]
   → alerta se ganho interdialítico > meta
〔 Em sessão · cronômetro 01:12:34 〕
   Monitor ao vivo: PA ▸ 128/80 · FC 76 · PTM 145 · fluxo UF 0.6 L/h
   [ + Intercorrência ]   [ eMAR: administrar medicação ]
〔 Encerramento 〕 Peso pós [70.1] · UF real [2.3]L · PA pós [122/78]
   → Kt/V 1.3 ✓ · URR 68% · nPCR 1.1  (calculado)
   [ Assinar evolução de enfermagem (SAE) ]
```

---

## 6. LME Inteligente (diferencial) — geração em ≤30s

```
┌ ← Gerar LME · Maria Silva ┐
│  Passo 1 — Medicamento                                                   │
│  〔 ◉ Alfaepoetina   ○ Sacarato férrico   ○ Sevelâmer   ○ Cinacalcete 〕  │
│      → PCDT aplicável: "Anemia na DRC (2024)"                            │
│                                                                          │
│  Passo 2 — Verificação automática                                        │
│  〔 ✅ Dados do paciente e médico preenchidos                          〕 │
│  〔 ✅ CID-10: N18.6 + D63.1                                           〕 │
│  〔 Exames obrigatórios do PCDT:                                       〕 │
│  〔   ✅ Hb 9.4 (14/07)   ✅ Ferritina 180 (14/07)   🔴 TSAT ausente   〕 │
│  〔   ⚠ Falta TSAT — [ registrar exame ] antes de emitir             〕 │
│                                                                          │
│  Passo 3 — Redação assistida (IA, revisável)                             │
│  〔 Anamnese   [ gerada do histórico + exames citados …            ] 〕   │
│  〔 Justificativa clínica (alinhada ao PCDT) [ … ]                    〕   │
│      🔎 exames citados: Hb, Ferritina (nunca inventa valores)            │
│                                                                          │
│  Passo 4 — Documentos                                                    │
│  [ Gerar PDF do LME ]   [ Termo de Esclarecimento (TER) ]                │
│  [ Assinar (step-up / ICP-Brasil) ]                                      │
│                                                                          │
│  Validade: 90 dias · Renovação em 1 clique ao vencer                      │
└──────────────────────────────────────────────────────────────────────┘

Estado "faltando exame": botão [Gerar PDF] desabilitado + AlertBanner vermelho.
Histórico de LMEs: lista com status (vigente/vencido/renovado) e cadeia de renovação.
```

---

## 7. Dashboard do Enfermeiro / Sala de HD (mapa)

```
┌ Sala de Hemodiálise · Turno manhã · 12 máquinas ┐
│  Grade de máquinas (cards de vidro por leito):                    │
│  〔 M1 · Maria S. ┊ 01:12 ┊ UF 2.3/2.5 ┊ PA ok ✓ 〕                │
│  〔 M2 · João P.  ┊ 00:40 ┊ 🟠 hipotensão registrada 〕            │
│  〔 M3 · livre 〕   〔 M4 · Ana L. ┊ recepção pendente 〕            │
│  ...                                                              │
│  eMAR pendente (3) · Recepções (2) · SAE a assinar (4)            │
└──────────────────────────────────────────────────────────────┘
```

---

## 8. Padrões transversais

- **Busca global (⌘/Ctrl-K):** paciente por nome/CNS/CPF em qualquer tela.
- **Estados vazios:** ilustração discreta + ação primária.
- **Loading:** skeletons dos cards (nunca tela branca).
- **Offline:** banner discreto "modo offline — sincronizando" + fila local.
- **Erros:** toast com ação de repetir; nunca perde dados digitados.
- **Assinatura:** sempre exige step-up auth; documento fechado fica imutável e com selo.
```

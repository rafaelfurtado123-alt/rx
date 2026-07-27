# Néfron — Fluxos Principais

Fluxos de negócio de alta fidelidade (Etapa 1). Notação simplificada; setas = passos.

---

## 1. Sessão de Hemodiálise (beira-leito, tablet-first)

```
[Escala do dia] ─► seleciona paciente (1 clique)
   │
   ▼
[Recepção]  peso_pré · PA · FC · Tª · queixas ──► valida ganho interdialítico
   │   (alerta se ganho > X% do peso seco)
   ▼
[Conferência da prescrição de HD]  Qb · Qd · UF prescrita/máx · dialisador · acesso
   │   (sistema mostra volume_calculado = peso_atual − peso_seco)
   ▼
[Início da sessão]  hd.sessao.inicio ──► máquina/dialisador ──► eMAR das medicações
   │
   ▼
[Monitoramento em tempo real]  hd.sessao_parametro (PA, FC, PTM, fluxo UF)
   │   Realtime (WSS) atualiza o painel; intercorrências registradas na hora
   ▼
[Intercorrência?] ── sim ─► hd.intercorrencia + conduta ─► (segue)
   │ não
   ▼
[Encerramento]  peso_pós · UF real · PA/FC pós ──► ureia pré/pós (se coletada)
   │
   ▼
[Cálculos automáticos]  Kt/V (Daugirdas), URR, nPCR ──► gráfico de adequação
   │
   ▼
[Evolução de enfermagem SAE]  semiautomática (puxa parâmetros) ──► assina
```

Meta de UX: recepção → início em **≤ 2 telas**; parâmetros com teclado numérico grande.

---

## 2. Prescrição Eletrônica (geral + HD)

```
[Prontuário do paciente] ─► "Prescrever" (1 clique)
   │
   ▼
[Tipo]  Geral  |  Hemodiálise  |  Enfermagem (SAE)
   │
   ├── GERAL ──► busca medicamento (ref.medicamento)
   │      │
   │      ▼  checagens em tempo real:
   │      • alergia (clinico.alergia)      → bloqueio/alerta
   │      • interação medicamentosa        → alerta com gravidade
   │      • dose máxima                     → alerta
   │      • ajuste renal por TFG (CKD-EPI)  → sugere dose ajustada
   │      ▼
   │   [Confirma itens] ─► assina (step-up auth p/ controlados) ─► eMAR gerado
   │
   └── HEMODIÁLISE ──► formulário nível Tasy:
          modalidade · duração · Qb · Qd · dialisador · acesso/ponto ·
          peso atual/seco · UF prescrita/máxima · perfil Na/bicarbonato ·
          heparinização · soluções/medicações da sessão
          ▼
       [volume_calculado automático] ─► assina ─► disponível na sala de HD
```

---

## 3. LME Inteligente (diferencial) — geração em ≤ 30s

```
[Paciente] ─► "Gerar LME" (1 clique) ─► escolhe medicamento CEAF
   │            (ex.: Alfaepoetina, Sevelâmer, Cinacalcete, Calcitriol…)
   ▼
[Carrega PCDT vigente]  ref.pcdt (versão + regras_json)
   │
   ▼
[Autopreenchimento]
   • Dados do paciente (nome, CNS, CPF, nascimento, endereço)
   • Dados do médico (nome, CRM/UF)
   • CID-10 principal (N18.x) + secundários exigidos
   • Exames MAIS RECENTES relevantes (Hb, ferritina, TSAT, PTH, Ca, P, TFG…)
   │
   ▼
[Validação de elegibilidade + exames obrigatórios]
   ┌─ falta exame / vencido (>Xd) ─► ALERTA vermelho, lista o que falta ─► (pausa)
   ├─ fora de meta do PCDT        ─► alerta amarelo com a regra citada
   └─ tudo ok                     ─► segue
   │
   ▼
[Redação assistida por IA (ancorada nos dados)]
   • Anamnese: história da DRC + TRS + exames citados (nunca inventa valores)
   • Justificativa clínica: alinhada ao PCDT, citando critérios atendidos
   │  (médico revisa/edita — marcado como rascunho até assinar)
   ▼
[Gera documentos]  PDF oficial do LME + Termo de Esclarecimento e Responsabilidade (TER)
   │
   ▼
[Assinatura]  eletrônica / ICP-Brasil (step-up auth) ─► status = assinado/vigente
   │
   ▼
[Controle de validade]  valido_ate = emitido_em + 90 dias
   │   • Dashboard mostra LMEs a vencer (D-15, D-7)
   ▼
[Renovação 1 clique]  clona laudo ─► reavalia exames ─► novo PDF ─► cadeia laudo_anterior_id
```

Regras: sem exame obrigatório presente e válido, **não emite** (só rascunho). Toda geração de
IA é auditada. Histórico completo de LMEs por paciente.

---

## 4. Evolução multiprofissional (tela única)

```
[Timeline do paciente] ─► "+ Evolução"
   │
   ▼
[SOAP estruturado]  S · O · A · P  +  texto livre
   │   • "Sumarizar com IA" → rascunho a partir das notas/últimos dados (revisável)
   │   • categoria: médica | enfermagem | nutrição | serviço social | psicologia
   ▼
[Assina]  ─► imutável ─► aparece na timeline filtrável por profissional/categoria
```

---

## 5. Alertas proativos (metas clínicas)

```
[Novo exame_resultado] ─► motor de regras (ref.parametro_clinico + PCDT)
   │
   ├─ Anemia:   Hb < 10 ou > 12 · TSAT < 20% · ferritina < 200/500
   ├─ DMO-DRC:  PTH fora da faixa por estágio · P alto · Ca alto/baixo
   ├─ Adequação: Kt/V < 1.2 (3x/sem)
   └─ ...
   ▼
[Prioriza (IA explica, não decide)] ─► card no dashboard do médico + sugestão de conduta
   │   (ex.: "considerar ajuste de eritropoetina — ver PCDT Anemia v.X")
```

---

## 6. Auditoria imutável (transversal)

```
Qualquer INSERT/UPDATE/soft-DELETE em tabela clínica
   ▼
[Trigger] ─► seguranca.audit_log
   • ator_id, acao, entidade, entidade_id, diff_json, ip, dispositivo, motivo
   • hash_atual = SHA256(payload || hash_anterior)   ← cadeia à prova de adulteração
   ▼
[Auditor] pode ler tudo (papel `auditor`), ninguém pode alterar/apagar log
```

---

## 7. Login + acesso a prontuário

```
[Login individual] ─► 2FA (TOTP) ─► seleciona unidade/vínculo ativo
   ▼
[Dashboard por perfil]  Médico | Enfermeiro | Técnico | Administrativo
   ▼
[Abre prontuário] ─► RLS confere vínculo unidade+paciente+papel
   │   • acesso a paciente sem vínculo → step-up + justificativa (quebra de sigilo registrada)
   ▼
[Ação em ≤ 2 cliques]  prescrever · evoluir · gerar LME · iniciar sessão
```

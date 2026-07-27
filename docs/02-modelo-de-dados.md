# Néfron — Modelo de Dados

Modelo lógico narrativo. O DDL executável está em [`db/schema.sql`](../db/schema.sql).
Organizado em **schemas** PostgreSQL por domínio.

---

## Schemas

| Schema | Responsabilidade |
|--------|------------------|
| `ref` | Catálogos e regras versionadas: CID-10, medicamentos, PCDT, exames, parâmetros clínicos, SIGTAP |
| `core` | Identidade organizacional: unidades, profissionais, papéis, vínculos, pacientes |
| `clinico` | Prontuário longitudinal: episódios, evolução SOAP, prescrições, exames/resultados, alergias, problemas |
| `hd` | Terapia renal substitutiva: prescrição de HD, sessões, parâmetros intradialíticos, acessos vasculares |
| `lme` | LME inteligente: laudos, itens, exames vinculados, termos, validade/renovação |
| `seguranca` | 2FA, consentimento LGPD, auditoria (hash-chain), assinaturas |
| `fatura` | SUS (APAC/BPA/SIGTAP) e TISS-ready |

---

## 1. `ref` — Referência (regras versionadas)

- **`ref.cid10`** — código, descrição. Foco em `N18.x` (DRC), `N17`, `E83.3` (hiperfosfatemia), etc.
- **`ref.medicamento`** — princípio ativo, apresentação, via, se é CEAF/alto custo, ajuste renal.
- **`ref.pcdt`** — protocolo (Anemia na DRC, DMO-DRC), versão, vigência, `regras_json`
  (critérios de elegibilidade, exames obrigatórios, metas, periodicidade). **Versionado.**
- **`ref.exame`** — LOINC-like, unidade, faixas de referência, se é "obrigatório para LME X".
- **`ref.parametro_clinico`** — metas/faixas (Hb 10–12, TSAT >20%, PTH por estágio…), versionadas.
- **`ref.sigtap`** — procedimentos SUS para faturamento.

> Regra: PCDT/doses/metas mudam por **nova linha versionada**, nunca por edição destrutiva.

---

## 2. `core` — Identidade

- **`core.unidade`** — clínica/serviço de diálise (tenant). CNES, endereço, tipo.
- **`core.profissional`** — vínculo a `auth.users` (Supabase). Nome, CPF, conselho
  (CRM/COREN), UF, especialidade.
- **`core.papel`** — `medico | enfermeiro | tecnico | administrativo | admin | auditor | paciente`.
- **`core.vinculo`** — N:N profissional × unidade × papel (um profissional pode ser médico
  em uma unidade e admin em outra). Base do RBAC/RLS.
- **`core.paciente`** — **prontuário único longitudinal**:
  - Demográficos, **CNS** (Cartão SUS), CPF, sexo, raça/cor, nascimento, contatos.
  - Convênio(s), acesso à rede.
  - Sorologia (HBsAg, anti-HCV, anti-HIV, anti-HBs) — coluna sensível (pgcrypto).
  - Esquema vacinal (Hepatite B etc.) → `core.vacina_paciente`.
  - Etiologia da DRC, estágio (CKD-EPI), data de início de TRS, turno de diálise.
- **`core.paciente_unidade`** — vínculo do paciente à(s) unidade(s) (chave para RLS).

---

## 3. `clinico` — Prontuário longitudinal

Tudo pendura em `paciente_id` e alimenta a **linha do tempo unificada**.

- **`clinico.episodio`** — consulta, internação, sessão de HD, intercorrência, telemedicina.
  É o "container" temporal exibido na timeline.
- **`clinico.evolucao`** — **SOAP estruturado** (`subjetivo`, `objetivo`, `avaliacao`, `plano`)
  + `texto_livre` + `resumo_ia` (rascunho) + `profissional_id` + `assinada_em`.
  Multiprofissional (médico/enf/téc/nutri) em tela única, filtrável por categoria.
- **`clinico.problema`** — lista de problemas (CID-10), status (ativo/resolvido).
- **`clinico.alergia`** — substância, reação, gravidade → alimenta alerta de prescrição.
- **`clinico.prescricao`** — cabeçalho: paciente, prescritor, unidade, tipo
  (`geral | hd | enfermagem_sae`), status, validade, assinatura.
- **`clinico.prescricao_item`** — medicamento/solução, dose, via, frequência, duração,
  `ajuste_renal_aplicado`, alertas disparados (interação/alergia/dose máx).
- **`clinico.emar`** — checagem eletrônica de administração (eMAR): item, horário previsto ×
  realizado, executante, status (administrado/recusado/omitido), lote.
- **`clinico.exame_resultado`** — exame (`ref.exame`), valor, unidade, data coleta, flag
  fora-de-faixa. Base dos **gráficos de tendência** (Hb, ferritina, TSAT, PTH, Ca, P, Kt/V).

---

## 4. `hd` — Hemodiálise (nível Tasy)

### 4.1 Acesso vascular
- **`hd.acesso_vascular`** — tipo (FAV, prótese/enxerto, cateter tunelizado, cateter temporário),
  lado, localização, data de confecção/implante, status, complicações.

### 4.2 Prescrição de HD (`hd.prescricao_hd`, 1:1 com `clinico.prescricao` tipo `hd`)
Campos equivalentes ao Tasy:
- `modalidade` (IHD, SLED, CVVH, CVVHD, CVVHDF, HDF online…)
- `duracao_min`, `qb_ml_min` (fluxo sanguíneo), `qd_ml_min` (fluxo do dialisato)
- `dialisador_modelo`, `dialisador_reuso`
- `acesso_id` (→ `hd.acesso_vascular`), `ponto_puncao`
- `peso_atual_kg`, `peso_seco_kg`, `uf_prescrita_l`, `uf_maxima_l`
- `perfil_sodio` (fixo/ramp/step + valores), `perfil_bicarbonato`, `condutividade`
- `temperatura_banho`, `heparinizacao` (esquema/dose/livre)
- `solucoes_json` / itens em `clinico.prescricao_item` (medicamentos durante a sessão)
- **`volume_calculado_l`** (derivado: peso_atual − peso_seco + estimativa de ingesta)

### 4.3 Sessão de HD (`hd.sessao`)
- Recepção: `peso_pre_kg`, `pa_pre`, `fc_pre`, `temp_pre`, `queixas`.
- Execução: `inicio`, `fim`, máquina, `hemodialisador`, técnico/enf responsável.
- Encerramento: `peso_pos_kg`, `uf_real_l`, `pa_pos`, `fc_pos`, intercorrências.
- **Derivados calculados:** `ktv`, `urr`, `npcr` (a partir de ureia pré/pós em `exame_resultado`).
- **`hd.sessao_parametro`** — série temporal intradialítica (PA, FC, Qb, PTM, fluxo de UF,
  condutividade) para o **monitor em tempo real** e integração futura com máquinas.
- **`hd.intercorrencia`** — hipotensão, cãibra, reação ao dialisador, etc. + conduta.

---

## 5. `lme` — LME Inteligente (diferencial)

- **`lme.laudo`** — cabeçalho do LME:
  - `paciente_id`, `medico_id`, `unidade_id`, `pcdt_id` (→ versão do protocolo aplicada).
  - `cid_principal` (N18.x), `cids_secundarios[]`.
  - `anamnese` (gerada da história + exames, editável), `justificativa` (ancorada no PCDT).
  - `status` (`rascunho | emitido | assinado | vigente | vencido | renovado | negado`).
  - `emitido_em`, `valido_ate` (**+90 dias**), `laudo_anterior_id` (cadeia de renovação).
  - `pdf_storage_path`, `assinatura_id`.
- **`lme.item`** — medicamento CEAF (Alfaepoetina, Darbepoetina, Sacarato férrico,
  Calcitriol, Paricalcitol, Sevelâmer, Carbonato de lantânio, Cinacalcete…),
  posologia, quantidade/mês, CID vinculado.
- **`lme.exame_vinculado`** — exames obrigatórios exigidos pelo PCDT × resultado usado
  (`exame_resultado_id`), com flag `presente`/`ausente`/`vencido` → **alerta se faltando**.
- **`lme.termo`** — Termo de Esclarecimento e Responsabilidade (TER): versão, texto, aceite,
  assinatura do paciente/responsável.

**Motor de geração (resumo do fluxo — ver doc 03):**
1. Médico escolhe o medicamento → sistema carrega o `pcdt` vigente.
2. Puxa dados do paciente/médico, CID, exames mais recentes.
3. Valida exames obrigatórios e critérios de elegibilidade (metas de Hb/TSAT/PTH…).
4. Gera anamnese + justificativa alinhadas ao PCDT (IA ancorada nos dados).
5. Alerta o que falta; ao completar, gera **PDF oficial + TER** e controla validade/renovação.

---

## 6. `seguranca` — Segurança e conformidade

- **`seguranca.fator_2fa`** — segredo TOTP/passkey por usuário.
- **`seguranca.consentimento`** — finalidade, base legal, versão do texto, aceite, revogação.
- **`seguranca.assinatura`** — assinatura eletrônica/ICP-Brasil de um documento
  (evolução, prescrição, LME): hash do conteúdo, certificado, timestamp.
- **`seguranca.audit_log`** — **append-only, hash-chain**: `id`, `ts`, `ator_id`, `acao`,
  `entidade`, `entidade_id`, `diff_json`, `ip`, `dispositivo`, `motivo`,
  `hash_anterior`, `hash_atual`. Preenchido por triggers.

---

## 7. `fatura` — Faturamento

- **`fatura.apac`** / **`fatura.bpa`** — produção SUS (TRS tem APAC específica).
- **`fatura.conta`** / **`fatura.conta_item`** — itens faturáveis (→ `ref.sigtap`), status.
- Estrutura **TISS-ready** (guias, tabelas próprias/AMB/TUSS) para convênios na fase 2.

---

## 8. ERD textual (principais relações)

```
core.paciente 1─┬─N clinico.episodio 1─N clinico.evolucao
                ├─N clinico.prescricao 1─N clinico.prescricao_item 1─N clinico.emar
                │                        └─(tipo=hd) 1─1 hd.prescricao_hd
                ├─N clinico.exame_resultado ──► ref.exame
                ├─N hd.acesso_vascular 1─N hd.sessao 1─N hd.sessao_parametro
                │                                     └─N hd.intercorrencia
                ├─N lme.laudo 1─┬─N lme.item ──► ref.medicamento
                │               ├─N lme.exame_vinculado ──► clinico.exame_resultado
                │               ├─1 lme.termo
                │               └──► ref.pcdt (versão aplicada)
                └─N seguranca.consentimento

core.profissional N─N core.unidade  (via core.vinculo + core.papel)
todas as tabelas clínicas ──trigger──► seguranca.audit_log (hash-chain)
```

---

## 9. Convenções

- PK: `uuid` (`gen_random_uuid()`); timestamps `timestamptz` (UTC).
- Auditoria de linha: `created_at`, `updated_at`, `created_by`, `updated_by`.
- Soft-delete clínico: `deleted_at` + versão (nunca `DELETE` físico de PHI).
- Enums via `CHECK`/tipos enum PG; catálogos grandes via tabela `ref`.
- Toda tabela com PHI: `unidade_id` + policies RLS (ver `db/schema.sql`).

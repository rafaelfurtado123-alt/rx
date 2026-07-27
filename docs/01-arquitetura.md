# Néfron — Arquitetura Completa

Documento de arquitetura de referência (Etapa 1). Cobre visão C4, camadas, segurança,
integrações, IA clínica e estratégia de deploy.

---

## 1. Princípios arquiteturais

1. **Domínio clínico no centro** — o núcleo (paciente, evolução, prescrição, sessão de HD, LME)
   é independente de framework; UI e infraestrutura são plugáveis.
2. **Segurança e auditoria por padrão** — RBAC + RLS no banco, log imutável, criptografia
   em trânsito e repouso, minimização de PHI. Nada é "adicionado depois".
3. **Offline-tolerante à beira-leito** — o app tolera perda de rede (fila local + sync),
   crítico para plantão e sala de diálise.
4. **2 cliques para qualquer ação frequente** — a arquitetura de navegação e as APIs são
   desenhadas para latência baixa e fluxos curtos.
5. **Regras clínicas versionadas** — PCDTs, doses, ajustes renais e critérios de LME vivem
   em tabelas versionadas, não em código, para atualização sem redeploy.

---

## 2. Visão C4 — Nível 1 (Contexto)

```
                    ┌─────────────────────────────────────────────┐
   Médico ──────────►                                             │
   Enfermeiro ──────►            Néfron (PEP Nefrológico)          ├──► DATASUS / e-SUS (futuro)
   Técnico ─────────►                                             ├──► SIGTAP / APAC / BPA (SUS)
   Administrativo ──►                                             ├──► CEAF / SES (LME)
   Paciente (fase 2)►                                             ├──► TISS / Convênios (fase 2)
                    └───────────────┬─────────────────────────────┤──► Máquinas de HD (HL7/FHIR - fase 3)
                                    │                             └──► ICP-Brasil (assinatura)
                                    ▼
                            Provedor de IA (sumarização/redação, PHI minimizado)
```

---

## 3. Visão C4 — Nível 2 (Contêineres)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTES (Flutter)                                 │
│   App Médico/Enf/Téc/Adm (iOS, Android, Tablet)   │   Web (Flutter Web)         │
└───────────────┬────────────────────────────────────────────────┬──────────────┘
                │ HTTPS (mTLS opcional) / WSS                      │
                ▼                                                  ▼
┌──────────────────────────────┐                   ┌───────────────────────────────┐
│   API Gateway / BFF          │                   │  Supabase Realtime (WSS)       │
│   (FastAPI, OpenAPI 3.1)     │◄──────────────────┤  eventos de sessão de HD,      │
│   AuthN/AuthZ, rate-limit    │                   │  dashboards ao vivo, presença  │
└───────┬──────────────────────┘                   └───────────────────────────────┘
        │
        ├──► Serviço Clínico (evolução, prescrição, HD, exames)
        ├──► Serviço LME (motor de regras PCDT + geração de laudo)
        ├──► Serviço PDF/Documentos (LME, termos, receitas)
        ├──► Serviço IA (sumarização/justificativa — orquestração + guardrails)
        ├──► Serviço Auditoria (append-only, hash-chain)
        └──► Serviço Faturamento (SIGTAP/APAC/BPA, TISS-ready)
                    │
                    ▼
        ┌───────────────────────────────────────────────────────────┐
        │  PostgreSQL 16 (Supabase)                                  │
        │  - Schemas: core, clinico, hd, lme, seguranca, fatura, ref │
        │  - RLS por perfil + unidade + vínculo profissional         │
        │  - pgcrypto (colunas sensíveis), pg_partman (partições)    │
        └───────────────────────────────────────────────────────────┘
        ┌───────────────────────────┐   ┌───────────────────────────┐
        │ Supabase Storage (S3)     │   │  Fila/Jobs (Celery+Redis / │
        │ PDFs, exames, anexos      │   │  Supabase Edge Functions)  │
        │ criptografados            │   │  LME em lote, renovações   │
        └───────────────────────────┘   └───────────────────────────┘
```

**Por que FastAPI + Supabase (e não só Supabase):**
Supabase entrega Auth, RLS, Realtime e Storage prontos. A camada FastAPI concentra a
**lógica clínica sensível** (motor de LME/PCDT, cálculos de Kt/V, geração de PDF assinável,
guardrails de IA) que não deve viver em client nem em policies SQL. RLS continua sendo a
**última linha de defesa** mesmo que a API falhe.

---

## 4. Camadas do backend (Clean/Hexagonal)

```
app/
├── api/            # Rotas FastAPI, schemas Pydantic (DTOs), OpenAPI
├── domain/         # Entidades e regras puras (Paciente, Prescricao, SessaoHD, LME)
│   ├── clinico/
│   ├── hd/
│   ├── lme/        # PCDT engine: elegibilidade, exames obrigatórios, validade
│   └── seguranca/
├── application/    # Casos de uso (orquestração), portas (interfaces)
├── infra/          # Adaptadores: repositórios SQLAlchemy, Supabase, IA, PDF, storage
├── workers/        # Jobs assíncronos (renovação de LME, relatórios ANVISA)
└── shared/         # Auditoria, i18n, unidades, validadores (CNS, CPF, CID)
```

Regra de dependência: `api → application → domain`; `infra` implementa portas do `domain`.
O `domain` não importa framework.

---

## 5. Segurança e conformidade (não negociável)

### 5.1 Autenticação
- Login individual (nunca compartilhado) via Supabase Auth (JWT).
- **2FA obrigatório** para perfis clínicos (TOTP; WebAuthn/passkey como evolução).
- Sessão com expiração curta + refresh rotativo; *step-up auth* para ações críticas
  (assinar LME, prescrever controlado, abrir prontuário de VIP).

### 5.2 Autorização — RBAC + ABAC
- Papéis: `medico`, `enfermeiro`, `tecnico`, `administrativo`, `admin`, `auditor`, `paciente`.
- Atributos: unidade/clínica, vínculo ativo com o paciente, plantão corrente.
- Aplicada em **três camadas**: (1) UI, (2) API (dependências FastAPI), (3) **RLS no Postgres**.

### 5.3 RLS (Row-Level Security)
Toda tabela com PHI tem policies. Exemplo de política de acesso a `clinico.evolucao`:
o usuário só lê linhas de pacientes de uma unidade à qual está vinculado e para a qual tem
papel com permissão de leitura clínica. Ver `db/schema.sql` (seção RLS).

### 5.4 Criptografia
- **Em trânsito:** TLS 1.3 obrigatório; HSTS; mTLS opcional para integrações.
- **Em repouso:** criptografia de disco (Supabase/cloud) + `pgcrypto` para colunas
  ultrassensíveis (ex.: sorologia, dados de identificação secundários).
- Storage de anexos criptografado; URLs assinadas de curta duração.

### 5.5 Auditoria imutável
- Tabela `seguranca.audit_log` **append-only** com *hash chain* (cada registro carrega o
  hash do anterior → detecção de adulteração).
- Registra: quem, o quê, quando, de onde (IP/dispositivo), valor antes/depois (diff),
  motivo (quando exigido). Triggers em todas as tabelas clínicas.
- Retenção mínima conforme CFM (prontuário: 20 anos).

### 5.6 LGPD
- `seguranca.consentimento` versionado por finalidade.
- Base legal registrada por operação (tutela da saúde / obrigação legal).
- Direitos do titular: exportação (portabilidade) e relatório de acessos.
- **Minimização de PHI na IA:** só o estritamente necessário é enviado; prompts e respostas
  são auditados; possibilidade de rodar modelo em ambiente controlado.

### 5.7 Versionamento de prontuário
- Nada é apagado: `UPDATE`/`DELETE` clínicos geram versão (soft-delete + histórico).
- Assinatura eletrônica por evolução/prescrição; documento fechado é imutável.

---

## 6. IA clínica auxiliar (guardrails)

| Uso | Entrada | Guardrail |
|-----|---------|-----------|
| Sumarização de evolução | Notas do episódio | Sempre revisado pelo médico antes de assinar; marcado como "rascunho IA" |
| Justificativa de LME | Exames + histórico + PCDT | Texto ancorado em dados reais; citação dos exames usados; nunca inventa valores |
| Alertas proativos | Séries laboratoriais | Regras determinísticas primeiro; IA só explica/prioriza |

Princípios: **a IA nunca decide, sempre sugere**; toda saída é atribuída, versionada e
auditada; PHI minimizado; opção de desligar por unidade.

---

## 7. Cálculos clínicos nativos (biblioteca `domain/hd`)

- **Kt/V (Daugirdas 2ª geração):**
  `Kt/V = -ln(R - 0.008·t) + (4 - 3.5·R)·UF/W`
  onde `R = ureia_pós/ureia_pré`, `t` = horas de sessão, `UF` = ultrafiltração (L),
  `W` = peso pós (kg).
- **nPCR (taxa de catabolismo proteico normalizada).**
- **URR** = `(1 - ureia_pós/ureia_pré)·100`.
- **Volume a ultrafiltrar** = `peso_atual − peso_seco (+ ganhos intradialíticos)`.
- **Ajuste renal de dose** por faixa de TFG (CKD-EPI) — tabela versionada.
- **Metas de anemia/DMO-DRC** conforme PCDT (Hb, ferritina, TSAT, PTH, Ca, P).

Todos com testes unitários e faixas de referência versionadas em `ref.parametro_clinico`.

---

## 8. Integrações

| Sistema | Protocolo | Fase |
|---------|-----------|------|
| Máquinas de HD | HL7 v2 / FHIR (Observation) | 3 |
| SUS — faturamento | SIGTAP, APAC, BPA (arquivos) | 1–2 |
| Convênios | TISS (XML) | 2 |
| CEAF / SES | PDF LME + interface futura | 1 |
| Laboratório | HL7 ORU / FHIR DiagnosticReport | 2 |
| Assinatura | ICP-Brasil PAdES | 1 (preparado) |

---

## 9. Observabilidade e resiliência

- Logs estruturados (JSON) + correlação por `request_id`.
- Métricas (Prometheus) e tracing (OpenTelemetry).
- Health checks + degradação graciosa (se IA cair, editor manual continua; se realtime cair,
  polling assume).
- **Backup automático** point-in-time (PITR) + testes de restauração periódicos.

---

## 10. Deploy

```
Dev  → Staging → Produção
- CI: lint (ruff), type (mypy), testes (pytest), migrations (alembic) validadas
- CD: build container FastAPI + build Flutter (web/app); migrations com aprovação
- Infra: Supabase gerenciado + container backend (Fly.io/Render/Cloud brasileiro p/ dados)
- Dados de saúde hospedados em região BR (residência de dados / LGPD)
```

---

## 11. Multi-tenant

Modelo **single-database, schema compartilhado com `unidade_id`** + RLS. Cada clínica/unidade
é um tenant; usuários podem ter vínculos em múltiplas unidades com papéis distintos.
Isolamento garantido por RLS, não por confiança no app.

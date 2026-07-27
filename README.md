# Néfron — Prontuário Eletrônico Nefrológico de Alta Performance

> **PEP focado em Nefrologia e Terapia Renal Substitutiva (TRS)** — mais rápido, bonito e
> clinicamente completo que Tasy e Nefrosys, com LGPD + CFM + ANVISA por padrão.

---

## 1. Nome do Sistema

Foram consideradas três opções premium:

| Nome | Conceito | Prós |
|------|----------|------|
| **Néfron** ✅ | A unidade funcional do rim | Curto, memorável em PT-BR, clínico, escalável como marca |
| RenalFlow | Fluxo de cuidado + fluxo de diálise (Qb/Qd) | Moderno, remete à HD |
| Aether Nephro | Leveza / glassmorphism | Premium, porém menos direto |

**Nome oficial escolhido: `Néfron`** — estilizado `néfron·` no produto.
Racional: identidade curta, pronunciável, imediatamente associada à nefrologia, funciona
como namespace técnico (`nefron-api`, `nefron-app`, `nefron.core`) e como marca visual.

---

## 2. Visão em uma frase

Um PEP longitudinal, **mobile/tablet-first**, com prescrição eletrônica nível Tasy
(inclusa prescrição completa de Hemodiálise), **LME inteligente** para medicamentos de alto
custo do CEAF nefrológico, e segurança/auditoria em conformidade com a legislação brasileira.

---

## 3. Estrutura do repositório

```
rx/
├── README.md                      ← este arquivo
├── docs/
│   ├── 01-arquitetura.md          ← arquitetura completa (C4, camadas, segurança, deploy)
│   ├── 02-modelo-de-dados.md      ← modelo de dados narrativo + ERD textual
│   ├── 03-fluxos-principais.md    ← fluxos: HD, LME, prescrição, auditoria
│   ├── 04-roadmap.md              ← fases de entrega
│   ├── 05-design-system.md        ← Design System néfron· (tokens, glass, componentes)
│   └── 06-wireframes.md           ← wireframes de alta fidelidade (texto)
├── app/                           ← frontend Flutter (Design System + telas)
│   └── lib/{theme,widgets}/       ← tokens e componentes reutilizáveis
└── db/
    ├── schema.sql                 ← schema PostgreSQL/Supabase completo
    └── seed.sql                   ← dados de referência (CID-10 nefro, PCDTs, catálogos)
```

---

## 4. Stack

- **Frontend:** Flutter (web + iOS + Android + tablet), Material 3 + Design System `néfron·`
- **Backend:** FastAPI (Python 3.12) — API REST/GraphQL, regras clínicas, geração de LME/PDF
- **Banco / Plataforma:** PostgreSQL 16 + Supabase (Auth, Realtime, Storage, RLS)
- **Gráficos:** fl_chart (Flutter)
- **PDF:** WeasyPrint / ReportLab (server-side, LME e termos oficiais)
- **Assinatura digital:** preparado para ICP-Brasil (PAdES) + fallback CFM
- **IA auxiliar:** camada de sumarização/redação (evolução + justificativa de LME) via provedor
  configurável, com **PHI minimizado** e trilha de auditoria de cada geração.

---

## 5. Status de entrega

- [x] **Etapa 1 — Arquitetura + Modelo de dados + Fluxos**
- [x] **Etapa 2 — Design System `néfron·` + wireframes** (`docs/05`, `docs/06`, `app/`)
- [ ] Etapa 3 — Módulo Autenticação + Dashboard
- [ ] Etapa 4 — Prontuário + Evolução
- [ ] Etapa 5 — Prescrição de HD
- [ ] Etapa 6 — LME Inteligente

Consulte `docs/04-roadmap.md` para o plano completo.

---

## 6. Conformidade (resumo)

LGPD (Lei 13.709/2018) · CFM Res. 1.821/2007 e 2.314/2022 (telemedicina/prontuário) ·
Manual de Certificação SBIS/CFM (NGS2) · ANVISA RDC de TRS · PCDT Anemia na DRC e
PCDT do Distúrbio Mineral Ósseo da DRC (DMO-DRC) · CEAF (Componente Especializado).

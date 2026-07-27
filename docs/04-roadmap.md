# Néfron — Roadmap de Entrega

## Etapa 1 — Fundação (ESTE COMMIT) ✅
- Arquitetura completa (C4, camadas, segurança, IA, deploy)
- Modelo de dados + schema SQL (`db/schema.sql`) + seed de referência
- Fluxos principais (HD, prescrição, LME, evolução, auditoria)

## Etapa 2 — Design System + Wireframes
- Design System `néfron·`: tokens (cor, tipografia, espaçamento), glassmorphism, dark mode,
  alto contraste, componentes Material 3 customizados.
- Wireframes de alta fidelidade (texto) de todas as telas-chave.

## Etapa 3 — Autenticação + Dashboard
- Login individual + 2FA (TOTP), seleção de vínculo/unidade.
- Dashboards por perfil (Médico, Enfermeiro, Técnico, Administrativo).
- RBAC + RLS operacionais.

## Etapa 4 — Prontuário + Evolução
- Cadastro completo do paciente, timeline unificada.
- Evolução SOAP multiprofissional + sumarização IA.
- Gráficos de tendência (Hb, ferritina, TSAT, PTH, Ca, P, Kt/V, peso seco).

## Etapa 5 — Prescrição de HD
- Prescrição geral (alergia/interação/dose/ajuste renal) + eMAR.
- Prescrição de HD nível Tasy + módulo de sessão + cálculo Kt/V/URR/nPCR.

## Etapa 6 — LME Inteligente
- Motor PCDT, autopreenchimento, validação de exames, redação IA, PDF + TER, validade/renovação.

## Fases posteriores
- Faturamento SUS/TISS · Relatórios ANVISA/censo/indicadores · Integração HL7/FHIR com máquinas
  · Portal do paciente · Assinatura ICP-Brasil produtiva.

---

### Ordem sugerida de implementação de código
`Auth+Dashboard → Prontuário+Evolução → Prescrição HD → LME Inteligente`
(conforme solicitado no comando original).

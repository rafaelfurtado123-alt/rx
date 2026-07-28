# Néfron — Integração VIDaaS (Certificado em Nuvem ICP-Brasil / CRM Digital)

Assinatura digital ICP-Brasil dos documentos oficiais (LME) usando o **VIDaaS**
(Valid Certificadora), o certificado em nuvem que médicos obtêm gratuitamente
pelo programa **CRM Digital** dos Conselhos Regionais de Medicina.

---

## 1. Como funciona (padrão API PSC ICP-Brasil)

```
Médico (app Néfron)                Backend Néfron                    VIDaaS (PSC)
      │  1. "Assinar com ICP"          │                                  │
      ├──────────────────────────────► │  2. POST /assinatura/vidaas/     │
      │                                │     autorizacao                  │
      │                                │  gera state + PKCE               │
      │ ◄──── QR / URL de autorização ─┤  (verifier/challenge S256)       │
      │                                │                                  │
      │  3. aprova no APP VIDaAS  ─────────────────────────────────────►  │
      │     (push com login_hint=CPF ou QR)                               │
      │                                │ ◄── 4. redirect callback ────────┤
      │                                │     ?code=...&state=...          │
      │                                │  5. troca code por access_token  │
      │                                │     (sessão de assinatura) ────► │
      │  6. app faz polling do status  │                                  │
      │ ◄──── status: autorizada ──────┤                                  │
      │  7. POST /assinatura/vidaas/   │                                  │
      │     lme/{id}                   │  8. SHA-256 do PDF oficial       │
      │                                │     POST hash ─────────────────► │
      │                                │ ◄── CMS/PKCS#7 (base64) ─────────┤
      │ ◄──── assinado ✓ ──────────────┤  9. grava seguranca.assinatura   │
      │                                │     (hash, .p7s, PDF exato)      │
```

Detalhes técnicos:
- **OAuth2 authorization_code + PKCE (S256)**, escopo `signature_session`.
- `login_hint` com o CPF do médico dispara o **push** no app VIDaaS.
- A assinatura é **CMS/PKCS#7 destacada** sobre o hash SHA-256
  (OID `2.16.840.1.101.3.4.2.1`) do PDF oficial do LME.
- O PDF é **determinístico** (`invariant` no ReportLab, rodapé sem timestamp
  de geração): o mesmo laudo sempre produz os mesmos bytes.
- O par **PDF assinado + .p7s** fica armazenado em `seguranca.assinatura`
  (`documento_b64` + `assinatura_b64`) e é verificável no **validador do ITI**
  (https://validar.iti.gov.br).

## 2. Configuração

```bash
# .env do backend
NEFRON_VIDAAS_BASE_URL=https://certificado.vidaas.com.br
NEFRON_VIDAAS_CLIENT_ID=<obtido no credenciamento junto à Valid>
NEFRON_VIDAAS_CLIENT_SECRET=<idem>
NEFRON_VIDAAS_REDIRECT_URI=https://sua-api/api/v1/assinatura/vidaas/callback
NEFRON_VIDAAS_MOCK=false
```

**Modo simulado** (dev/homologação): sem `CLIENT_ID` ou com
`NEFRON_VIDAAS_MOCK=true`, o provedor mock assume — o fluxo inteiro roda sem
rede, o app mostra o botão "simular aprovação" e a assinatura sai marcada como
`vidaas-mock` (explicitamente **não válida** juridicamente).

Aplique a migração: `psql "$DB" -f db/vidaas.sql`.

## 3. Rotas

| Rota | Uso |
|------|-----|
| `POST /api/v1/assinatura/vidaas/autorizacao` | Inicia sessão (state + URL/QR) — médico |
| `GET  /api/v1/assinatura/vidaas/callback` | Redirect do PSC (pública, validada por state) |
| `GET  /api/v1/assinatura/vidaas/autorizacao/{state}` | Polling: pendente/autorizada/expirada/erro |
| `POST /api/v1/assinatura/vidaas/lme/{laudo_id}` | Assina o PDF do LME (exige laudo emitido) |
| `GET  /api/v1/assinatura/{id}/p7s` | Assinatura destacada (.p7s) |
| `GET  /api/v1/assinatura/{id}/documento` | Cópia exata do PDF assinado |

Regras: assinar é ato do **médico** (RBAC); o LME precisa estar **emitido**
(a assinatura eletrônica interna vem antes); a sessão VIDaaS expira (~30 min)
e cada autorização pertence ao profissional que a iniciou.

## 3.1 Login por certificado digital

O mesmo certificado em nuvem serve como **método de login** (substitui senha +
TOTP — a aprovação no app do PSC já é autenticação forte: posse do celular +
PIN/biometria + certificado ICP-Brasil do titular):

| Rota | Uso |
|------|-----|
| `POST /api/v1/auth/vidaas/login` `{cpf}` | Inicia (CPF deve pertencer a profissional ativo) |
| `GET  /api/v1/auth/vidaas/login/{state}` | Polling; quando autorizada, **consome** a sessão (uso único) e devolve `{refresh_token, vinculos}` — mesmo formato do 2FA |

O fluxo segue normal: seleção de contexto → access token. No app, botão
"Entrar com certificado digital (VIDaaS)" na tela de login.

## 3.2 Receitas (simples e controle especial)

| Rota | Uso |
|------|-----|
| `GET  /api/v1/prescricoes/{id}/receita/pdf` | Receituário em PDF (header `X-Receita-Tipo`) |
| `POST /api/v1/assinatura/vidaas/prescricao/{id}` | Assina a receita com o certificado em nuvem |

- A receita exige prescrição **assinada eletronicamente** (409 caso contrário).
- Tipo automático: qualquer item com `ref.medicamento.controlado = true`
  (Portaria SVS/MS 344/98) gera **Receituário de Controle Especial em 2 vias**
  (1ª farmácia / 2ª paciente) com box de identificação do emitente; senão,
  receituário simples.
- PDF determinístico; o par PDF assinado + `.p7s` fica em
  `seguranca.assinatura` como nos LMEs.
- Migração: `psql "$DB" -f db/receitas.sql` (flag `controlado` + finalidade da
  sessão VIDaaS).
- No app: após assinar a prescrição, o sistema oferece a assinatura ICP da
  receita no mesmo fluxo de QR/push.

## 4. Passos para produção

1. **Credenciamento junto à Valid**: registrar a aplicação (client_id/secret +
   redirect URI) no programa de parceiros VIDaaS. Os endpoints exatos e campos
   do payload de assinatura devem ser conferidos contra a documentação oficial
   da API PSC entregue no credenciamento (são configuráveis por env).
2. **Cifrar `access_token` e `assinatura_b64`** em repouso (pgcrypto/KMS).
3. **PAdES**: evoluir de assinatura destacada para assinatura embutida no PDF
   (pyHanko com assinador externo), mantendo o mesmo fluxo VIDaaS.
4. **Carimbo do tempo** (ACT) se exigido pelo fluxo da SES.
5. Outros PSCs (BirdID, NeoID, SafeID) usam a MESMA API PSC do ITI — basta
   parametrizar `base_url`/credenciais, o `AssinaturaProvider` já isola isso.

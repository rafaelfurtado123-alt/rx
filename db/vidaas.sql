-- =============================================================================
-- Néfron — Integração VIDaaS (certificado em nuvem ICP-Brasil / CRM Digital)
-- Rode após o schema.sql:  psql -d nefron -f db/vidaas.sql
-- =============================================================================

-- Sessão de autorização OAuth2/PKCE junto ao PSC (VIDaaS).
-- O access_token é de vida curta (sessão de assinatura); cifrar em produção.
create table if not exists seguranca.vidaas_sessao (
  id               uuid primary key default gen_random_uuid(),
  profissional_id  uuid not null references core.profissional(id),
  state            text not null unique,
  code_verifier    text not null,
  access_token     text,
  token_expira_em  timestamptz,
  status           text not null default 'pendente'
                   check (status in ('pendente','autorizada','expirada','erro')),
  created_at       timestamptz not null default now()
);

create index if not exists idx_vidaas_sessao_prof
  on seguranca.vidaas_sessao (profissional_id, created_at desc);

-- Conteúdo da assinatura destacada (CMS/PKCS#7 em base64) gerada pelo PSC e
-- cópia exata do documento assinado (PDF em base64) — o par PDF + .p7s é o
-- que se verifica no validador ITI.
alter table seguranca.assinatura
  add column if not exists assinatura_b64 text,
  add column if not exists documento_b64 text;

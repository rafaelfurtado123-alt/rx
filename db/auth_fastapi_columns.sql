-- =============================================================================
-- Néfron — Colunas de credencial para auth próprio da API (FastAPI)
-- =============================================================================
-- Como o auth é próprio (não Supabase Auth), as credenciais ficam no
-- profissional. Rode após o schema.sql.
-- =============================================================================

alter table core.profissional
  add column if not exists senha_hash   text,          -- Argon2
  add column if not exists totp_secret  text,          -- segredo TOTP (cifrar em prod)
  add column if not exists totp_ativo   boolean not null default false,
  add column if not exists ultimo_login timestamptz;

-- Índice para busca por e-mail no login
create index if not exists idx_profissional_email on core.profissional (email);

-- =============================================================================
-- Néfron — Contexto de RLS para auth próprio da API (FastAPI)
-- =============================================================================
-- O schema.sql define os helpers de RLS usando auth.uid() (modelo Supabase Auth).
-- Como optamos por AUTH PRÓPRIO no FastAPI, redefinimos os helpers para lerem o
-- GUC de sessão `app.profissional_id`, que a API define por transação
-- (ver app/core/database.py :: set_rls_context).
--
-- Rode este arquivo APÓS o schema.sql:
--   psql -d nefron -f db/schema.sql
--   psql -d nefron -f db/rls_fastapi_context.sql
-- =============================================================================

-- Profissional autenticado na transação atual (nulo se não definido)
create or replace function core.profissional_atual() returns uuid as $$
  select nullif(current_setting('app.profissional_id', true), '')::uuid
$$ language sql stable;

-- Unidades às quais o profissional atual tem vínculo ativo
create or replace function core.minhas_unidades() returns setof uuid as $$
  select v.unidade_id
  from core.vinculo v
  where v.profissional_id = core.profissional_atual() and v.ativo
$$ language sql stable;

-- O profissional atual possui algum dos papéis informados?
create or replace function core.tenho_papel(papeis core.tipo_papel[]) returns boolean as $$
  select exists (
    select 1 from core.vinculo v
    where v.profissional_id = core.profissional_atual()
      and v.ativo and v.papel = any(papeis)
  )
$$ language sql stable;

-- Observação: as POLICIES do schema.sql permanecem válidas — elas apenas chamam
-- core.minhas_unidades() e core.tenho_papel(), agora dirigidas pelo GUC.

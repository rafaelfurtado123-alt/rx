-- =============================================================================
-- Néfron — Escala de diálise (agenda recorrente semanal)
-- Rode após o schema.sql:  psql -d nefron -f db/escala.sql
-- =============================================================================
-- Modelo de clínica de diálise: o paciente tem vaga fixa em turno + dias da
-- semana + máquina (ex.: 2ª/4ª/6ª manhã, máquina M03). dias_semana usa ISO:
-- 1=segunda ... 7=domingo.
-- =============================================================================

create table if not exists hd.escala (
  id            uuid primary key default gen_random_uuid(),
  paciente_id   uuid not null references core.paciente(id),
  unidade_id    uuid not null references core.unidade(id),
  turno         text not null check (turno in ('manha','tarde','noite')),
  dias_semana   smallint[] not null,          -- ISO 1..7
  maquina       text,
  ativo         boolean not null default true,
  inicio        date not null default current_date,
  fim           date,
  created_at    timestamptz not null default now()
);

create index if not exists idx_escala_unidade on hd.escala (unidade_id, turno)
  where ativo;

alter table hd.escala enable row level security;

create policy escala_rls on hd.escala for all
  using (unidade_id in (select core.minhas_unidades())
         or core.tenho_papel(array['auditor']::core.tipo_papel[]))
  with check (unidade_id in (select core.minhas_unidades()));

-- =============================================================================
-- Néfron — Ambulatório conservador + segmento do paciente + equipe multi
-- Rode após receitas.sql:  psql -d nefron -f db/ambulatorio.sql
-- =============================================================================

-- 1) Novo papel: equipe multiprofissional (nutrição, psicologia, serviço
--    social, farmácia, fisioterapia) — segmento próprio de login/dashboard.
alter type core.tipo_papel add value if not exists 'equipe_multi';

-- 2) Segmento de cuidado do paciente renal: ambulatório conservador ou TRS.
--    Pacientes legados (todos em HD até aqui) permanecem 'hemodialise'.
alter table core.paciente
  add column if not exists segmento text not null default 'hemodialise'
  check (segmento in ('conservador','hemodialise','dialise_peritoneal','transplante'));

create index if not exists idx_paciente_segmento on core.paciente (segmento)
  where deleted_at is null;

-- 3) Agenda do ambulatório conservador (consultas nefrológicas).
create table if not exists clinico.consulta_agendada (
  id               uuid primary key default gen_random_uuid(),
  paciente_id      uuid not null references core.paciente(id),
  unidade_id       uuid not null references core.unidade(id),
  profissional_id  uuid references core.profissional(id),
  data_hora        timestamptz not null,
  tipo             text not null default 'retorno'
                   check (tipo in ('primeira_consulta','retorno','preparo_trs')),
  status           text not null default 'agendada'
                   check (status in ('agendada','realizada','faltou','cancelada')),
  observacao       text,
  episodio_id      uuid references clinico.episodio(id),
  created_at       timestamptz not null default now()
);

create index if not exists idx_consulta_unidade_data
  on clinico.consulta_agendada (unidade_id, data_hora);

alter table clinico.consulta_agendada enable row level security;

create policy consulta_rls on clinico.consulta_agendada for all
  using (unidade_id in (select core.minhas_unidades())
         or core.tenho_papel(array['auditor']::core.tipo_papel[]))
  with check (unidade_id in (select core.minhas_unidades()));

-- 4) Cadastro de paciente via API: separa INSERT de UPDATE no RLS.
--    A política antiga (FOR ALL) exigia vínculo paciente↔unidade JÁ existente
--    no INSERT — impossível para um paciente novo. Agora: qualquer profissional
--    clínico/administrativo da unidade pode CRIAR; leitura/edição continuam
--    condicionadas ao vínculo.
drop policy if exists pac_write on core.paciente;

create policy pac_insert on core.paciente for insert
  with check (core.tenho_papel(
    array['medico','enfermeiro','administrativo','admin']::core.tipo_papel[]));

create policy pac_update on core.paciente for update
  using (exists (
    select 1 from core.paciente_unidade pu
    where pu.paciente_id = core.paciente.id
      and pu.unidade_id in (select core.minhas_unidades())))
  with check (exists (
    select 1 from core.paciente_unidade pu
    where pu.paciente_id = core.paciente.id
      and pu.unidade_id in (select core.minhas_unidades())));

-- INSERT do vínculo paciente↔unidade na própria unidade do criador
drop policy if exists pac_uni_rls on core.paciente_unidade;
create policy pac_uni_rls on core.paciente_unidade for all
  using (unidade_id in (select core.minhas_unidades())
         or core.tenho_papel(array['auditor']::core.tipo_papel[]))
  with check (unidade_id in (select core.minhas_unidades()));

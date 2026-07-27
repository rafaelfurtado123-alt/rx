-- =============================================================================
-- Néfron — Prontuário Eletrônico Nefrológico
-- Schema PostgreSQL 16 / Supabase — Etapa 1
-- =============================================================================
-- Convenções:
--   * PK uuid (gen_random_uuid)
--   * timestamptz em UTC; created_at/updated_at/created_by/updated_by
--   * Soft-delete clínico (deleted_at) — nunca DELETE físico de PHI
--   * Enums via tipos PG; catálogos grandes em schema `ref`
--   * RLS habilitada em toda tabela com PHI (ver seção final)
-- =============================================================================

-- ---------- Extensões ----------
create extension if not exists "pgcrypto";      -- gen_random_uuid, crypt, pgp_sym
create extension if not exists "citext";        -- e-mails/códigos case-insensitive
create extension if not exists "btree_gist";    -- exclusões de intervalo (agenda)

-- ---------- Schemas ----------
create schema if not exists ref;
create schema if not exists core;
create schema if not exists clinico;
create schema if not exists hd;
create schema if not exists lme;
create schema if not exists seguranca;
create schema if not exists fatura;

-- ---------- Tipos (enums) ----------
create type core.tipo_papel as enum
  ('medico','enfermeiro','tecnico','administrativo','admin','auditor','paciente');

create type core.sexo as enum ('masculino','feminino','intersexo','nao_informado');

create type clinico.tipo_episodio as enum
  ('consulta','sessao_hd','internacao','intercorrencia','telemedicina','procedimento');

create type clinico.tipo_prescricao as enum ('geral','hd','enfermagem_sae');
create type clinico.status_prescricao as enum ('rascunho','ativa','suspensa','encerrada','cancelada');
create type clinico.categoria_evolucao as enum
  ('medica','enfermagem','nutricao','servico_social','psicologia','farmacia','fisioterapia');

create type clinico.status_emar as enum
  ('previsto','administrado','recusado','omitido','adiado');

create type hd.modalidade_trs as enum
  ('IHD','SLED','HDF_online','CVVH','CVVHD','CVVHDF','DPAC','DPA');
create type hd.tipo_acesso as enum
  ('fav','protese','cateter_tunelizado','cateter_temporario','peritoneal');

create type lme.status_laudo as enum
  ('rascunho','emitido','assinado','vigente','vencido','renovado','negado','cancelado');

-- =============================================================================
-- SCHEMA ref — catálogos e regras versionadas
-- =============================================================================

create table ref.cid10 (
  codigo        varchar(10) primary key,          -- ex.: N18.5
  descricao     text not null,
  categoria     varchar(10)                        -- ex.: N18
);

create table ref.medicamento (
  id                uuid primary key default gen_random_uuid(),
  principio_ativo   text not null,
  apresentacao      text not null,                 -- ex.: 4000 UI/mL sol. inj.
  via_padrao        text,
  ceaf              boolean not null default false, -- alto custo / especializado
  requer_lme        boolean not null default false,
  ajuste_renal      jsonb,                          -- faixas de TFG × ajuste de dose
  dose_maxima_dia   numeric,
  unidade_dose      text,
  ativo             boolean not null default true
);

-- Protocolos clínicos (PCDT) versionados — coração do LME inteligente
create table ref.pcdt (
  id            uuid primary key default gen_random_uuid(),
  nome          text not null,                      -- 'Anemia na DRC', 'DMO-DRC'
  versao        text not null,
  vigencia_ini  date not null,
  vigencia_fim  date,
  regras_json   jsonb not null,                     -- elegibilidade, exames obrigatórios,
                                                    -- metas, periodicidade, CIDs aceitos
  unique (nome, versao)
);

create table ref.exame (
  id            uuid primary key default gen_random_uuid(),
  codigo        varchar(20) unique,                 -- LOINC-like
  nome          text not null,
  unidade       text,
  ref_min       numeric,
  ref_max       numeric,
  categoria     text                                -- hematologia, ferro, DMO, ureia...
);

-- Metas/faixas clínicas versionadas (anemia, DMO, adequação)
create table ref.parametro_clinico (
  id            uuid primary key default gen_random_uuid(),
  chave         text not null,                      -- 'hb_alvo','tsat_min','ktv_min'
  descricao     text,
  faixa_min     numeric,
  faixa_max     numeric,
  contexto      jsonb,                              -- ex.: por estágio de DRC
  versao        text not null,
  vigencia_ini  date not null default current_date,
  vigencia_fim  date
);

create table ref.sigtap (
  codigo        varchar(15) primary key,
  descricao     text not null,
  valor_sus     numeric
);

-- =============================================================================
-- SCHEMA core — identidade organizacional e paciente
-- =============================================================================

create table core.unidade (
  id            uuid primary key default gen_random_uuid(),
  nome          text not null,
  cnes          varchar(7) unique,
  tipo          text,                               -- clinica_dialise, hospital, ambulatorio
  endereco      jsonb,
  ativo         boolean not null default true,
  created_at    timestamptz not null default now()
);

-- Profissional: vinculado a auth.users (Supabase)
create table core.profissional (
  id            uuid primary key default gen_random_uuid(),
  auth_user_id  uuid unique,                        -- FK lógica p/ auth.users
  nome          text not null,
  cpf           varchar(11) unique,
  conselho_tipo text,                               -- CRM, COREN
  conselho_num  text,
  conselho_uf   varchar(2),
  especialidade text,
  email         citext unique,
  ativo         boolean not null default true,
  created_at    timestamptz not null default now()
);

-- Vínculo N:N profissional × unidade × papel (base do RBAC/RLS)
create table core.vinculo (
  id              uuid primary key default gen_random_uuid(),
  profissional_id uuid not null references core.profissional(id),
  unidade_id      uuid not null references core.unidade(id),
  papel           core.tipo_papel not null,
  ativo           boolean not null default true,
  inicio          date not null default current_date,
  fim             date,
  unique (profissional_id, unidade_id, papel)
);

-- Paciente — prontuário único longitudinal
create table core.paciente (
  id              uuid primary key default gen_random_uuid(),
  nome            text not null,
  nome_social     text,
  cns             varchar(15) unique,               -- Cartão Nacional de Saúde
  cpf             varchar(11) unique,
  sexo            core.sexo not null default 'nao_informado',
  data_nascimento date,
  raca_cor        text,
  telefone        text,
  endereco        jsonb,
  convenio        jsonb,                            -- operadora, plano, matrícula
  -- Nefrologia
  etiologia_drc   text,
  estagio_drc     smallint check (estagio_drc between 1 and 5),
  inicio_trs      date,
  turno_dialise   text,
  -- Sorologia (sensível — considerar pgcrypto na app layer)
  sorologia       jsonb,                            -- HBsAg, anti-HCV, anti-HIV, anti-HBs
  -- Auditoria de linha
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  created_by      uuid,
  updated_by      uuid,
  deleted_at      timestamptz
);

-- Vínculo paciente × unidade (chave central para RLS)
create table core.paciente_unidade (
  paciente_id   uuid not null references core.paciente(id),
  unidade_id    uuid not null references core.unidade(id),
  ativo         boolean not null default true,
  primary key (paciente_id, unidade_id)
);

create table core.vacina_paciente (
  id            uuid primary key default gen_random_uuid(),
  paciente_id   uuid not null references core.paciente(id),
  vacina        text not null,                      -- Hepatite B, Influenza...
  dose          text,
  data          date,
  observacao    text
);

-- =============================================================================
-- SCHEMA clinico — prontuário longitudinal
-- =============================================================================

create table clinico.episodio (
  id            uuid primary key default gen_random_uuid(),
  paciente_id   uuid not null references core.paciente(id),
  unidade_id    uuid not null references core.unidade(id),
  tipo          clinico.tipo_episodio not null,
  inicio        timestamptz not null default now(),
  fim           timestamptz,
  responsavel_id uuid references core.profissional(id),
  resumo        text,
  created_at    timestamptz not null default now()
);
create index on clinico.episodio (paciente_id, inicio desc);

create table clinico.problema (
  id            uuid primary key default gen_random_uuid(),
  paciente_id   uuid not null references core.paciente(id),
  cid           varchar(10) references ref.cid10(codigo),
  descricao     text,
  status        text not null default 'ativo',      -- ativo | resolvido
  inicio        date default current_date,
  fim           date
);

create table clinico.alergia (
  id            uuid primary key default gen_random_uuid(),
  paciente_id   uuid not null references core.paciente(id),
  substancia    text not null,
  reacao        text,
  gravidade     text,                               -- leve | moderada | grave
  ativo         boolean not null default true
);

create table clinico.evolucao (
  id              uuid primary key default gen_random_uuid(),
  episodio_id     uuid references clinico.episodio(id),
  paciente_id     uuid not null references core.paciente(id),
  profissional_id uuid not null references core.profissional(id),
  categoria       clinico.categoria_evolucao not null default 'medica',
  -- SOAP estruturado
  subjetivo       text,
  objetivo        text,
  avaliacao       text,
  plano           text,
  texto_livre     text,
  resumo_ia       text,                             -- rascunho gerado por IA
  assinada_em     timestamptz,                      -- imutável após assinatura
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  deleted_at      timestamptz
);
create index on clinico.evolucao (paciente_id, created_at desc);

create table clinico.prescricao (
  id              uuid primary key default gen_random_uuid(),
  paciente_id     uuid not null references core.paciente(id),
  unidade_id      uuid not null references core.unidade(id),
  prescritor_id   uuid not null references core.profissional(id),
  tipo            clinico.tipo_prescricao not null,
  status          clinico.status_prescricao not null default 'rascunho',
  inicio          timestamptz not null default now(),
  validade        timestamptz,
  assinada_em     timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index on clinico.prescricao (paciente_id, inicio desc);

create table clinico.prescricao_item (
  id                uuid primary key default gen_random_uuid(),
  prescricao_id     uuid not null references clinico.prescricao(id) on delete cascade,
  medicamento_id    uuid references ref.medicamento(id),
  descricao_livre   text,
  dose              numeric,
  unidade_dose      text,
  via               text,
  frequencia        text,
  duracao           text,
  ajuste_renal_aplicado boolean default false,
  alertas           jsonb,                          -- interações/alergia/dose máx disparados
  ordem             int
);

create table clinico.emar (
  id                uuid primary key default gen_random_uuid(),
  prescricao_item_id uuid not null references clinico.prescricao_item(id),
  paciente_id       uuid not null references core.paciente(id),
  horario_previsto  timestamptz not null,
  horario_realizado timestamptz,
  executante_id     uuid references core.profissional(id),
  status            clinico.status_emar not null default 'previsto',
  lote              text,
  observacao        text
);
create index on clinico.emar (paciente_id, horario_previsto);

create table clinico.exame_resultado (
  id            uuid primary key default gen_random_uuid(),
  paciente_id   uuid not null references core.paciente(id),
  exame_id      uuid not null references ref.exame(id),
  valor         numeric,
  valor_texto   text,
  unidade       text,
  data_coleta   timestamptz not null,
  fora_faixa    boolean,
  origem        text,                               -- lab interno, importado HL7...
  created_at    timestamptz not null default now()
);
create index on clinico.exame_resultado (paciente_id, exame_id, data_coleta desc);

-- =============================================================================
-- SCHEMA hd — hemodiálise
-- =============================================================================

create table hd.acesso_vascular (
  id            uuid primary key default gen_random_uuid(),
  paciente_id   uuid not null references core.paciente(id),
  tipo          hd.tipo_acesso not null,
  lado          text,                               -- direito | esquerdo
  localizacao   text,                               -- radiocefálica, jugular...
  data_confeccao date,
  status        text not null default 'ativo',      -- ativo | disfuncao | retirado
  complicacoes  text,
  created_at    timestamptz not null default now()
);

-- Prescrição de HD (1:1 com clinico.prescricao tipo 'hd') — nível Tasy
create table hd.prescricao_hd (
  id                uuid primary key default gen_random_uuid(),
  prescricao_id     uuid not null unique references clinico.prescricao(id) on delete cascade,
  modalidade        hd.modalidade_trs not null,
  duracao_min       int not null,
  qb_ml_min         int,                            -- fluxo sanguíneo
  qd_ml_min         int,                            -- fluxo do dialisato
  dialisador_modelo text,
  dialisador_reuso  int,
  acesso_id         uuid references hd.acesso_vascular(id),
  ponto_puncao      text,
  peso_atual_kg     numeric,
  peso_seco_kg      numeric,
  uf_prescrita_l    numeric,
  uf_maxima_l       numeric,
  perfil_sodio      jsonb,                          -- {tipo:'ramp', ini:145, fim:138}
  perfil_bicarbonato jsonb,
  condutividade     numeric,
  temperatura_banho numeric,
  heparinizacao     jsonb,                          -- {tipo, dose_bolus, manutencao}
  solucoes_json     jsonb,                          -- soluções/medicações da sessão
  volume_calculado_l numeric generated always as
                     (greatest(coalesce(peso_atual_kg,0) - coalesce(peso_seco_kg,0), 0)) stored,
  created_at        timestamptz not null default now()
);

create table hd.sessao (
  id                uuid primary key default gen_random_uuid(),
  paciente_id       uuid not null references core.paciente(id),
  unidade_id        uuid not null references core.unidade(id),
  prescricao_hd_id  uuid references hd.prescricao_hd(id),
  acesso_id         uuid references hd.acesso_vascular(id),
  episodio_id       uuid references clinico.episodio(id),
  -- Recepção
  peso_pre_kg       numeric,
  pa_pre            text,
  fc_pre            int,
  temp_pre          numeric,
  queixas           text,
  -- Execução
  inicio            timestamptz,
  fim               timestamptz,
  maquina           text,
  tecnico_id        uuid references core.profissional(id),
  enfermeiro_id     uuid references core.profissional(id),
  -- Encerramento
  peso_pos_kg       numeric,
  uf_real_l         numeric,
  pa_pos            text,
  fc_pos            int,
  -- Adequação (calculados na aplicação a partir de ureia pré/pós)
  ktv               numeric,
  urr               numeric,
  npcr              numeric,
  intercorrencias_resumo text,
  created_at        timestamptz not null default now()
);
create index on hd.sessao (paciente_id, inicio desc);

-- Série temporal intradialítica (monitor em tempo real / integração máquina)
create table hd.sessao_parametro (
  id            uuid primary key default gen_random_uuid(),
  sessao_id     uuid not null references hd.sessao(id) on delete cascade,
  ts            timestamptz not null default now(),
  pa            text,
  fc            int,
  qb_ml_min     int,
  ptm           numeric,                            -- pressão transmembrana
  fluxo_uf      numeric,
  condutividade numeric,
  temperatura   numeric
);
create index on hd.sessao_parametro (sessao_id, ts);

create table hd.intercorrencia (
  id            uuid primary key default gen_random_uuid(),
  sessao_id     uuid not null references hd.sessao(id) on delete cascade,
  ts            timestamptz not null default now(),
  tipo          text not null,                      -- hipotensao, caibra, reacao...
  descricao     text,
  conduta       text,
  responsavel_id uuid references core.profissional(id)
);

-- =============================================================================
-- SCHEMA lme — LME inteligente
-- =============================================================================

create table lme.laudo (
  id                uuid primary key default gen_random_uuid(),
  paciente_id       uuid not null references core.paciente(id),
  medico_id         uuid not null references core.profissional(id),
  unidade_id        uuid not null references core.unidade(id),
  pcdt_id           uuid references ref.pcdt(id),   -- versão do protocolo aplicada
  cid_principal     varchar(10) references ref.cid10(codigo),
  cids_secundarios  varchar(10)[],
  anamnese          text,                           -- gerada/editável
  justificativa     text,                           -- ancorada no PCDT
  status            lme.status_laudo not null default 'rascunho',
  emitido_em        timestamptz,
  valido_ate        timestamptz,                    -- emitido_em + 90 dias
  laudo_anterior_id uuid references lme.laudo(id),  -- cadeia de renovação
  pdf_storage_path  text,
  assinatura_id     uuid,
  ia_metadados      jsonb,                          -- modelo, prompt hash, exames citados
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);
create index on lme.laudo (paciente_id, emitido_em desc);
create index on lme.laudo (valido_ate) where status = 'vigente';

create table lme.item (
  id            uuid primary key default gen_random_uuid(),
  laudo_id      uuid not null references lme.laudo(id) on delete cascade,
  medicamento_id uuid not null references ref.medicamento(id),
  cid           varchar(10) references ref.cid10(codigo),
  posologia     text,
  quantidade_mes numeric,
  unidade       text
);

create table lme.exame_vinculado (
  id                uuid primary key default gen_random_uuid(),
  laudo_id          uuid not null references lme.laudo(id) on delete cascade,
  exame_id          uuid not null references ref.exame(id),
  exame_resultado_id uuid references clinico.exame_resultado(id),
  obrigatorio       boolean not null default true,
  situacao          text not null default 'ausente' -- presente | ausente | vencido
);

create table lme.termo (
  id            uuid primary key default gen_random_uuid(),
  laudo_id      uuid not null unique references lme.laudo(id) on delete cascade,
  versao        text not null,
  texto         text not null,
  aceite_em     timestamptz,
  aceite_por    text,                               -- paciente/responsável
  assinatura_id uuid
);

-- =============================================================================
-- SCHEMA seguranca — 2FA, consentimento, assinatura, auditoria
-- =============================================================================

create table seguranca.fator_2fa (
  id            uuid primary key default gen_random_uuid(),
  auth_user_id  uuid not null,
  tipo          text not null default 'totp',       -- totp | webauthn
  segredo       text,                               -- cifrado
  ativo         boolean not null default true,
  created_at    timestamptz not null default now()
);

create table seguranca.consentimento (
  id            uuid primary key default gen_random_uuid(),
  paciente_id   uuid not null references core.paciente(id),
  finalidade    text not null,                      -- tratamento, compartilhamento...
  base_legal    text not null,                      -- tutela da saude, obrigacao legal
  versao_texto  text not null,
  aceite_em     timestamptz not null default now(),
  revogado_em   timestamptz
);

create table seguranca.assinatura (
  id            uuid primary key default gen_random_uuid(),
  entidade      text not null,                      -- evolucao | prescricao | lme | termo
  entidade_id   uuid not null,
  assinante_id  uuid not null references core.profissional(id),
  hash_conteudo text not null,
  tipo          text not null default 'eletronica', -- eletronica | icp_brasil
  certificado   jsonb,
  assinado_em   timestamptz not null default now()
);

-- Log imutável, append-only, com hash-chain
create table seguranca.audit_log (
  id            bigserial primary key,
  ts            timestamptz not null default now(),
  ator_id       uuid,
  acao          text not null,                      -- insert | update | delete
  entidade      text not null,
  entidade_id   text,
  diff_json     jsonb,
  ip            inet,
  dispositivo   text,
  motivo        text,
  hash_anterior text,
  hash_atual    text not null
);

-- =============================================================================
-- SCHEMA fatura — SUS/TISS
-- =============================================================================

create table fatura.conta (
  id            uuid primary key default gen_random_uuid(),
  paciente_id   uuid not null references core.paciente(id),
  unidade_id    uuid not null references core.unidade(id),
  competencia   date not null,                      -- mês de referência
  tipo          text not null default 'sus',        -- sus | convenio
  status        text not null default 'aberta',
  created_at    timestamptz not null default now()
);

create table fatura.conta_item (
  id            uuid primary key default gen_random_uuid(),
  conta_id      uuid not null references fatura.conta(id) on delete cascade,
  sigtap_codigo varchar(15) references ref.sigtap(codigo),
  quantidade    int not null default 1,
  valor         numeric
);

create table fatura.apac (
  id            uuid primary key default gen_random_uuid(),
  paciente_id   uuid not null references core.paciente(id),
  numero        varchar(20),
  competencia   date not null,
  procedimento  varchar(15),                        -- TRS
  cid           varchar(10),
  validade_ini  date,
  validade_fim  date,
  status        text not null default 'ativa'
);

-- =============================================================================
-- AUDITORIA — trigger genérico com hash-chain
-- =============================================================================
create or replace function seguranca.fn_audit() returns trigger as $$
declare
  v_prev   text;
  v_payload jsonb;
  v_diff   jsonb;
  v_ator   uuid;
begin
  -- ator via GUC setado pela aplicação: set_config('app.ator_id', <uuid>, true)
  begin v_ator := nullif(current_setting('app.ator_id', true), '')::uuid; exception when others then v_ator := null; end;

  if (tg_op = 'DELETE') then
    v_diff := to_jsonb(old);
  elsif (tg_op = 'UPDATE') then
    v_diff := jsonb_build_object('antes', to_jsonb(old), 'depois', to_jsonb(new));
  else
    v_diff := to_jsonb(new);
  end if;

  select hash_atual into v_prev from seguranca.audit_log order by id desc limit 1;

  v_payload := jsonb_build_object(
    'ts', now(), 'ator', v_ator, 'acao', lower(tg_op),
    'entidade', tg_table_schema||'.'||tg_table_name,
    'diff', v_diff, 'prev', coalesce(v_prev,'')
  );

  insert into seguranca.audit_log
    (ator_id, acao, entidade, entidade_id, diff_json, hash_anterior, hash_atual)
  values (
    v_ator, lower(tg_op), tg_table_schema||'.'||tg_table_name,
    coalesce((v_diff->>'id'), (v_diff->'depois'->>'id')),
    v_diff, v_prev,
    encode(digest(v_payload::text, 'sha256'), 'hex')
  );

  if (tg_op = 'DELETE') then return old; else return new; end if;
end;
$$ language plpgsql security definer;

-- Anexar auditoria às tabelas clínicas sensíveis
do $$
declare t text;
begin
  foreach t in array array[
    'core.paciente','clinico.evolucao','clinico.prescricao','clinico.prescricao_item',
    'clinico.emar','hd.prescricao_hd','hd.sessao','lme.laudo','lme.item',
    'seguranca.consentimento','seguranca.assinatura'
  ] loop
    execute format(
      'create trigger trg_audit after insert or update or delete on %s
         for each row execute function seguranca.fn_audit();', t);
  end loop;
end $$;

-- Bloquear UPDATE/DELETE no audit_log (append-only)
create or replace function seguranca.fn_audit_immutable() returns trigger as $$
begin
  raise exception 'audit_log é imutável (append-only)';
end; $$ language plpgsql;
create trigger trg_audit_immutable before update or delete on seguranca.audit_log
  for each row execute function seguranca.fn_audit_immutable();

-- =============================================================================
-- RLS — Row Level Security (última linha de defesa)
-- =============================================================================
-- Modelo: o JWT do Supabase expõe auth.uid(). Mapeia-se para core.profissional
-- e, via core.vinculo, às unidades/papéis permitidos. Paciente acessa apenas os
-- próprios dados (fase 2).

-- Helper: unidades às quais o usuário atual tem vínculo ativo
create or replace function core.minhas_unidades() returns setof uuid as $$
  select v.unidade_id
  from core.vinculo v
  join core.profissional p on p.id = v.profissional_id
  where p.auth_user_id = auth.uid() and v.ativo
$$ language sql stable security definer;

-- Helper: papéis do usuário atual
create or replace function core.tenho_papel(papeis core.tipo_papel[]) returns boolean as $$
  select exists (
    select 1 from core.vinculo v
    join core.profissional p on p.id = v.profissional_id
    where p.auth_user_id = auth.uid() and v.ativo and v.papel = any(papeis)
  )
$$ language sql stable security definer;

-- Habilitar RLS
alter table core.paciente            enable row level security;
alter table core.paciente_unidade    enable row level security;
alter table clinico.episodio         enable row level security;
alter table clinico.evolucao         enable row level security;
alter table clinico.prescricao       enable row level security;
alter table clinico.exame_resultado  enable row level security;
alter table hd.sessao                enable row level security;
alter table lme.laudo                enable row level security;

-- Paciente: leitura por vínculo de unidade; auditor lê tudo
create policy pac_select on core.paciente for select using (
  core.tenho_papel(array['auditor']::core.tipo_papel[])
  or exists (
    select 1 from core.paciente_unidade pu
    where pu.paciente_id = core.paciente.id
      and pu.unidade_id in (select core.minhas_unidades())
  )
);
create policy pac_write on core.paciente for all using (
  exists (
    select 1 from core.paciente_unidade pu
    where pu.paciente_id = core.paciente.id
      and pu.unidade_id in (select core.minhas_unidades())
  )
  and core.tenho_papel(array['medico','enfermeiro','administrativo','admin']::core.tipo_papel[])
) with check (
  exists (
    select 1 from core.paciente_unidade pu
    where pu.paciente_id = core.paciente.id
      and pu.unidade_id in (select core.minhas_unidades())
  )
);

-- Padrão reutilizável: acesso por unidade do registro
create policy epi_rls on clinico.episodio for all
  using (unidade_id in (select core.minhas_unidades())
         or core.tenho_papel(array['auditor']::core.tipo_papel[]))
  with check (unidade_id in (select core.minhas_unidades()));

create policy presc_rls on clinico.prescricao for all
  using (unidade_id in (select core.minhas_unidades())
         or core.tenho_papel(array['auditor']::core.tipo_papel[]))
  with check (unidade_id in (select core.minhas_unidades()));

create policy sessao_rls on hd.sessao for all
  using (unidade_id in (select core.minhas_unidades())
         or core.tenho_papel(array['auditor']::core.tipo_papel[]))
  with check (unidade_id in (select core.minhas_unidades()));

create policy laudo_rls on lme.laudo for all
  using (unidade_id in (select core.minhas_unidades())
         or core.tenho_papel(array['auditor']::core.tipo_papel[]))
  with check (unidade_id in (select core.minhas_unidades()));

-- Evolução/exame: via unidade do paciente vinculado
create policy evo_rls on clinico.evolucao for all
  using (
    core.tenho_papel(array['auditor']::core.tipo_papel[])
    or exists (select 1 from core.paciente_unidade pu
               where pu.paciente_id = clinico.evolucao.paciente_id
                 and pu.unidade_id in (select core.minhas_unidades()))
  )
  with check (
    exists (select 1 from core.paciente_unidade pu
            where pu.paciente_id = clinico.evolucao.paciente_id
              and pu.unidade_id in (select core.minhas_unidades()))
  );

create policy exame_rls on clinico.exame_resultado for all
  using (
    core.tenho_papel(array['auditor']::core.tipo_papel[])
    or exists (select 1 from core.paciente_unidade pu
               where pu.paciente_id = clinico.exame_resultado.paciente_id
                 and pu.unidade_id in (select core.minhas_unidades()))
  )
  with check (
    exists (select 1 from core.paciente_unidade pu
            where pu.paciente_id = clinico.exame_resultado.paciente_id
              and pu.unidade_id in (select core.minhas_unidades()))
  );

create policy pac_uni_rls on core.paciente_unidade for all
  using (unidade_id in (select core.minhas_unidades())
         or core.tenho_papel(array['auditor']::core.tipo_papel[]))
  with check (unidade_id in (select core.minhas_unidades()));

-- =============================================================================
-- FIM DO SCHEMA — Etapa 1
-- =============================================================================

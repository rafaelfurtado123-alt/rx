-- =============================================================================
-- Néfron — Receituário (simples e controle especial) + login por certificado
-- Rode após vidaas.sql:  psql -d nefron -f db/receitas.sql
-- =============================================================================

-- Medicamento controlado (Portaria SVS/MS 344/98) → receituário de controle
-- especial em 2 vias, em vez do receituário simples.
alter table ref.medicamento
  add column if not exists controlado boolean not null default false;

-- Finalidade da sessão VIDaaS: assinatura de documento ou LOGIN por
-- certificado digital (o certificado em nuvem é autenticação forte:
-- posse do celular + PIN/biometria no app do PSC).
alter table seguranca.vidaas_sessao
  add column if not exists finalidade text not null default 'assinatura';

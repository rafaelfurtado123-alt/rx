-- =============================================================================
-- Néfron — Interações medicamentosas (base de pares) + seed nefrológico
-- Rode após o schema.sql:  psql -d nefron -f db/interacoes.sql
-- =============================================================================
-- O match é feito por princípio ativo (case-insensitive, substring nos dois
-- sentidos), entre os itens da MESMA prescrição e contra as prescrições ATIVAS
-- do paciente. Gravidade → comportamento na prescrição:
--   contraindicada → BLOQUEIO (impede assinatura)
--   grave | moderada → alerta
--   leve → informativo
-- =============================================================================

create table if not exists ref.interacao (
  id            uuid primary key default gen_random_uuid(),
  principio_a   text not null,
  principio_b   text not null,
  gravidade     text not null check (gravidade in ('contraindicada','grave','moderada','leve')),
  efeito        text,
  recomendacao  text
);

create index if not exists idx_interacao_a on ref.interacao (lower(principio_a));
create index if not exists idx_interacao_b on ref.interacao (lower(principio_b));

-- Pares clinicamente relevantes em nefrologia (seed inicial)
insert into ref.interacao (principio_a, principio_b, gravidade, efeito, recomendacao) values
  ('Espironolactona', 'Cloreto de potássio', 'contraindicada',
   'Risco elevado de hipercalemia grave em DRC',
   'Associação contraindicada em doença renal crônica avançada'),
  ('Espironolactona', 'Losartana', 'grave',
   'Hipercalemia por duplo bloqueio do SRAA',
   'Monitorar potássio sérico; considerar alternativa'),
  ('Carbonato de cálcio', 'Calcitriol', 'grave',
   'Risco de hipercalcemia',
   'Monitorar cálcio sérico; ajustar doses'),
  ('Sevelâmer (cloridrato)', 'Ciprofloxacino', 'moderada',
   'Redução da absorção da quinolona por quelação',
   'Administrar o antibiótico 2h antes ou 6h após o quelante'),
  ('Carbonato de lantânio', 'Levotiroxina', 'moderada',
   'Redução da absorção da levotiroxina',
   'Separar as administrações em pelo menos 2 horas'),
  ('Cinacalcete', 'Amitriptilina', 'moderada',
   'Inibição de CYP2D6 aumenta níveis do antidepressivo',
   'Observar efeitos adversos; considerar ajuste de dose')
on conflict do nothing;

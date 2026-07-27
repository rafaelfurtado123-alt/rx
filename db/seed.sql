-- =============================================================================
-- Néfron — Dados de referência (seed) — Etapa 1
-- Catálogos nefrológicos: CID-10, exames, medicamentos CEAF, PCDT, metas, SIGTAP
-- =============================================================================

-- ---------- CID-10 (foco nefrológico) ----------
insert into ref.cid10 (codigo, descricao, categoria) values
  ('N18',   'Doença renal crônica', 'N18'),
  ('N18.1', 'Doença renal crônica estágio 1', 'N18'),
  ('N18.2', 'Doença renal crônica estágio 2', 'N18'),
  ('N18.3', 'Doença renal crônica estágio 3', 'N18'),
  ('N18.4', 'Doença renal crônica estágio 4', 'N18'),
  ('N18.5', 'Doença renal crônica estágio 5', 'N18'),
  ('N18.6', 'Doença renal em estágio final (diálise)', 'N18'),
  ('N17',   'Insuficiência renal aguda', 'N17'),
  ('D63.1', 'Anemia em doença renal crônica', 'D63'),
  ('E83.3', 'Distúrbios do metabolismo do fósforo', 'E83'),
  ('N25.8', 'Distúrbio mineral ósseo da DRC (hiperparatireoidismo secundário)', 'N25'),
  ('Z99.2', 'Dependência de diálise renal', 'Z99')
on conflict (codigo) do nothing;

-- ---------- Exames (base dos gráficos e do LME) ----------
insert into ref.exame (codigo, nome, unidade, ref_min, ref_max, categoria) values
  ('HB',    'Hemoglobina', 'g/dL', 10, 12, 'hematologia'),
  ('HT',    'Hematócrito', '%', 33, 36, 'hematologia'),
  ('FERR',  'Ferritina', 'ng/mL', 200, 500, 'ferro'),
  ('TSAT',  'Saturação de transferrina', '%', 20, 50, 'ferro'),
  ('PTH',   'Paratormônio (PTHi)', 'pg/mL', 130, 585, 'dmo'),
  ('CA',    'Cálcio total', 'mg/dL', 8.4, 9.5, 'dmo'),
  ('P',     'Fósforo', 'mg/dL', 3.5, 5.5, 'dmo'),
  ('VITD',  '25-OH Vitamina D', 'ng/mL', 30, 100, 'dmo'),
  ('UREPRE','Ureia pré-diálise', 'mg/dL', null, null, 'adequacao'),
  ('UREPOS','Ureia pós-diálise', 'mg/dL', null, null, 'adequacao'),
  ('CREAT', 'Creatinina', 'mg/dL', null, null, 'funcao_renal'),
  ('TFG',   'Taxa de filtração glomerular (CKD-EPI)', 'mL/min/1.73m²', null, null, 'funcao_renal'),
  ('KTV',   'Kt/V (single-pool)', '', 1.2, null, 'adequacao'),
  ('ALB',   'Albumina', 'g/dL', 3.5, 5.0, 'nutricao')
on conflict (codigo) do nothing;

-- ---------- Medicamentos CEAF nefrológicos (alto custo / LME) ----------
insert into ref.medicamento (principio_ativo, apresentacao, via_padrao, ceaf, requer_lme, dose_maxima_dia, unidade_dose) values
  ('Alfaepoetina',             '4000 UI solução injetável',     'SC/IV', true, true, null, 'UI'),
  ('Darbepoetina alfa',        '40 mcg solução injetável',      'SC/IV', true, true, null, 'mcg'),
  ('Sacarato de hidróxido férrico (Fe III)', '100 mg/5mL sol. inj.', 'IV', true, true, null, 'mg'),
  ('Calcitriol',               '0,25 mcg cápsula',              'VO',    true, true, null, 'mcg'),
  ('Paricalcitol',             '5 mcg/mL solução injetável',    'IV',    true, true, null, 'mcg'),
  ('Sevelâmer (cloridrato)',   '800 mg comprimido',             'VO',    true, true, null, 'mg'),
  ('Carbonato de lantânio',    '500 mg comprimido mastigável',  'VO',    true, true, null, 'mg'),
  ('Cinacalcete',              '30 mg comprimido',              'VO',    true, true, null, 'mg')
on conflict do nothing;

-- ---------- PCDT (regras versionadas — resumo estruturado) ----------
insert into ref.pcdt (nome, versao, vigencia_ini, regras_json) values
(
  'Anemia na Doença Renal Crônica', '2024',
  date '2024-01-01',
  jsonb_build_object(
    'cids_aceitos', jsonb_build_array('N18.3','N18.4','N18.5','N18.6','D63.1'),
    'exames_obrigatorios', jsonb_build_array('HB','FERR','TSAT'),
    'metas', jsonb_build_object('hb_min',10,'hb_max',12,'tsat_min',20,'ferritina_min',200),
    'periodicidade_exames_dias', 90,
    'medicamentos', jsonb_build_array('Alfaepoetina','Darbepoetina alfa',
                                      'Sacarato de hidróxido férrico (Fe III)')
  )
),
(
  'Distúrbio Mineral Ósseo da DRC (DMO-DRC)', '2024',
  date '2024-01-01',
  jsonb_build_object(
    'cids_aceitos', jsonb_build_array('N18.4','N18.5','N18.6','E83.3','N25.8'),
    'exames_obrigatorios', jsonb_build_array('PTH','CA','P'),
    'metas', jsonb_build_object('p_min',3.5,'p_max',5.5,'ca_min',8.4,'ca_max',9.5,
                                'pth_dialise_min',130,'pth_dialise_max',585),
    'periodicidade_exames_dias', 90,
    'medicamentos', jsonb_build_array('Calcitriol','Paricalcitol','Sevelâmer (cloridrato)',
                                      'Carbonato de lantânio','Cinacalcete')
  )
)
on conflict (nome, versao) do nothing;

-- ---------- Metas/faixas clínicas versionadas ----------
insert into ref.parametro_clinico (chave, descricao, faixa_min, faixa_max, versao) values
  ('hb_alvo',   'Hemoglobina alvo na anemia da DRC',        10,   12,   '2024'),
  ('tsat_min',  'Saturação de transferrina mínima',         20,   null, '2024'),
  ('ferritina_min','Ferritina mínima',                      200,  null, '2024'),
  ('p_alvo',    'Fósforo alvo',                             3.5,  5.5,  '2024'),
  ('ca_alvo',   'Cálcio alvo',                              8.4,  9.5,  '2024'),
  ('pth_dialise','PTH alvo em diálise',                     130,  585,  '2024'),
  ('ktv_min',   'Kt/V mínimo (3x/semana)',                  1.2,  null, '2024')
on conflict do nothing;

-- ---------- SIGTAP (exemplos de TRS) ----------
insert into ref.sigtap (codigo, descricao, valor_sus) values
  ('0305010107', 'Hemodiálise (máximo 3 sessões por semana)', null),
  ('0305010204', 'Hemodiálise em pacientes com sorologia positiva', null),
  ('0305010115', 'Diálise peritoneal ambulatorial contínua (CAPD)', null)
on conflict (codigo) do nothing;

-- =============================================================================
-- FIM DO SEED
-- =============================================================================

-- REAL = mart_metas_mensal; SEM_PIX = REAL menos pontos Pix; grão (mês, cenário) único;
-- pontos adicionais >= 0 e, quando > 0, levam o varejo exatamente a 20% do novo total.
with c as (select * from {{ ref('mart_cenarios_meta') }}),
m as (select * from {{ ref('mart_metas_mensal') }})

select 'real_diverge' as teste, c.mes as detalhe
from c join m using (mes)
where c.cenario = 'REAL' and c.pontos_liquidos_total <> m.pontos_liquidos_total
union all
select 'sem_pix_diverge', c.mes
from c join m using (mes)
where c.cenario = 'SEM_PIX' and c.pontos_liquidos_total <> m.pontos_liquidos_total - m.pontos_pix
union all
select 'grao_duplicado', mes || '/' || cenario from c group by mes, cenario having count(*) > 1
union all
select 'adicionais_negativos', mes || '/' || cenario
from c where pontos_varejo_adicionais_estrito < 0 or pontos_varejo_adicionais_amplo < 0
union all
select 'adicionais_nao_levam_a_20pct_estrito', mes || '/' || cenario
from c
where pontos_varejo_adicionais_estrito > 0
  and abs((pontos_varejo_estrito + pontos_varejo_adicionais_estrito) / (pontos_liquidos_total + pontos_varejo_adicionais_estrito) - 0.2) > 1e-9
union all
select 'adicionais_nao_levam_a_20pct_amplo', mes || '/' || cenario
from c
where pontos_varejo_adicionais_amplo > 0
  and abs((pontos_varejo_amplo + pontos_varejo_adicionais_amplo) / (pontos_liquidos_total + pontos_varejo_adicionais_amplo) - 0.2) > 1e-9

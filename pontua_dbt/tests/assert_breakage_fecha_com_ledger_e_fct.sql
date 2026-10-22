-- (1) saldo acumulado do último mês = soma de todos os pontos do ledger;
-- (2) resgatados líquidos somados = pontos_liquidos de fct_resgates;
-- (3) em cada mês a variação de saldo é explicada só por op 1, 100, 2, 14, 3 e 103 (sem operação esquecida).
with ult as (select saldo_acumulado from {{ ref('mart_breakage_mensal') }} order by mes desc limit 1),
led as (select sum(points) as total from {{ ref('stg_points_ledger') }}),
resg as (select sum(pontos_resgatados_liquidos) as total from {{ ref('mart_breakage_mensal') }}),
fct as (select sum(pontos_liquidos) as total from {{ ref('fct_resgates') }})

select 'saldo_final' as teste, ult.saldo_acumulado as valor_mart, led.total as valor_referencia
from ult, led where ult.saldo_acumulado <> led.total
union all
select 'resgatados_liquidos', resg.total, fct.total from resg, fct where resg.total <> fct.total
union all
select 'componentes_' || mes, variacao_saldo,
       pontos_creditados_acumulo + pontos_migrados - pontos_resgatados_brutos + pontos_estornados
       - pontos_expirados_regular - pontos_expirados_migracao
from {{ ref('mart_breakage_mensal') }}
where variacao_saldo <> pontos_creditados_acumulo + pontos_migrados - pontos_resgatados_brutos + pontos_estornados
       - pontos_expirados_regular - pontos_expirados_migracao

-- Soma de pontos_liquidos de fct_resgates = -(soma de points do ledger com operation_code in (2, 14)).
-- Valor esperado fixo: 320.027.439. Retorna linha (= falha) se qualquer comparação divergir.
with fct as (select sum(pontos_liquidos) as total from {{ ref('fct_resgates') }}),
ledger as (
    select -sum(points) as total from {{ ref('stg_points_ledger') }} where operation_code in (2, 14)
)

select fct.total as total_fct, ledger.total as total_ledger, 320027439 as total_esperado
from fct, ledger
where fct.total <> ledger.total or fct.total <> 320027439

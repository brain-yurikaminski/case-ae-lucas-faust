-- Grão: mês × tipo_resgate, com grade completa (meses sem resgate de um tipo aparecem com zero).
-- Base: fct_resgates (itens APROVADO e ESTORNADO). reais_por_ponto considera só itens APROVADO.
with meses as (
    select distinct mes from {{ ref('fct_resgates') }}
),

tipos as (
    select distinct tipo_resgate from {{ ref('fct_resgates') }}
),

agg as (
    select
        mes,
        tipo_resgate,
        sum(pontos_liquidos) as pontos_liquidos,
        count(*) as itens,
        sum(valor_reais) as valor_reais,
        sum(valor_reais) filter (where status = 'APROVADO') as valor_reais_aprovados,
        sum(pontos_brutos) filter (where status = 'APROVADO') as pontos_brutos_aprovados
    from {{ ref('fct_resgates') }}
    group by mes, tipo_resgate
)

select
    m.mes,
    t.tipo_resgate,
    cast(coalesce(a.pontos_liquidos, 0) as bigint) as pontos_liquidos,
    coalesce(a.itens, 0) as itens,
    coalesce(a.valor_reais, 0) as valor_reais,
    a.valor_reais_aprovados / nullif(a.pontos_brutos_aprovados, 0) as reais_por_ponto
from meses m
cross join tipos t
left join agg a on a.mes = m.mes and a.tipo_resgate = t.tipo_resgate

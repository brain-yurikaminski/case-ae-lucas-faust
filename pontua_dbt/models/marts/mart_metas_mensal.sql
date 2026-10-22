-- Grão: 1 linha por mês (mes, horário de Brasília). Base: fct_resgates (pontos_liquidos).
-- Percentuais em fração (0 a 1). Colunas do relatório em escala 0 a 100, como o operador reporta.
with resg as (
    select
        mes,
        cast(sum(pontos_liquidos) as bigint) as pontos_liquidos_total,
        cast(coalesce(sum(pontos_liquidos) filter (where tipo_resgate = 'AEREO'), 0) as bigint) as pontos_aereo,
        cast(coalesce(sum(pontos_liquidos) filter (where tipo_resgate = 'VAREJO_PRODUTO'), 0) as bigint) as pontos_varejo_produto,
        cast(coalesce(sum(pontos_liquidos) filter (where tipo_resgate = 'TRANSFERENCIA_PARCEIRO'), 0) as bigint) as pontos_transferencia_parceiro,
        cast(coalesce(sum(pontos_liquidos) filter (where tipo_resgate = 'PIX'), 0) as bigint) as pontos_pix
    from {{ ref('fct_resgates') }}
    group by mes
),

pct as (
    select
        *,
        pontos_aereo / nullif(pontos_liquidos_total, 0) as pct_aereo,
        pontos_varejo_produto / nullif(pontos_liquidos_total, 0) as pct_varejo_produto,
        pontos_transferencia_parceiro / nullif(pontos_liquidos_total, 0) as pct_transferencia_parceiro,
        pontos_pix / nullif(pontos_liquidos_total, 0) as pct_pix
    from resg
)

select
    p.mes,
    p.pontos_liquidos_total,
    p.pontos_aereo,
    p.pontos_varejo_produto,
    p.pontos_transferencia_parceiro,
    p.pontos_pix,
    p.pct_aereo,
    p.pct_varejo_produto,
    p.pct_transferencia_parceiro,
    p.pct_pix,
    p.pct_varejo_produto as pct_varejo_estrito,
    p.pct_varejo_produto + p.pct_transferencia_parceiro as pct_varejo_amplo,
    p.pct_aereo >= 0.5 as atende_meta_aereo,
    p.pct_varejo_produto >= 0.2 as atende_meta_varejo_estrito,
    (p.pct_varejo_produto + p.pct_transferencia_parceiro) >= 0.2 as atende_meta_varejo_amplo,
    r.aereas_pct as relatorio_aereas_pct,
    r.varejo_pct as relatorio_varejo_pct,
    r.pix_pct as relatorio_pix_pct,
    r.aereas_pct - p.pct_aereo * 100 as dif_aereas_pp,
    r.varejo_pct - (p.pct_varejo_produto + p.pct_transferencia_parceiro) * 100 as dif_varejo_amplo_pp,
    r.pix_pct - p.pct_pix * 100 as dif_pix_pp
from pct p
left join {{ ref('stg_relatorio_mensal_cliente') }} r using (mes)

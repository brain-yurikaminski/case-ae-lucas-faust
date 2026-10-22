-- Grão: mês (2026-06 a 2026-09) × cenário (REAL ou SEM_PIX). Base: mart_metas_mensal.
-- SEM_PIX é aritmética: subtrai os pontos Pix do total e mantém o resto igual (não assume troca por outro tipo).
with m as (
    select * from {{ ref('mart_metas_mensal') }}
    where mes between '2026-06' and '2026-09'
),

cen as (
    select
        mes, 'REAL' as cenario,
        pontos_liquidos_total as total,
        pontos_aereo as aereo,
        pontos_varejo_produto as varejo_estrito,
        pontos_varejo_produto + pontos_transferencia_parceiro as varejo_amplo
    from m
    union all
    select
        mes, 'SEM_PIX' as cenario,
        pontos_liquidos_total - pontos_pix,
        pontos_aereo,
        pontos_varejo_produto,
        pontos_varejo_produto + pontos_transferencia_parceiro
    from m
)

select
    mes,
    cenario,
    total as pontos_liquidos_total,
    aereo as pontos_aereo,
    varejo_estrito as pontos_varejo_estrito,
    varejo_amplo as pontos_varejo_amplo,
    aereo / total as pct_aereo,
    varejo_estrito / total as pct_varejo_estrito,
    varejo_amplo / total as pct_varejo_amplo,
    aereo / total >= 0.5 as atende_meta_aereo,
    varejo_estrito / total >= 0.2 as atende_meta_varejo_estrito,
    varejo_amplo / total >= 0.2 as atende_meta_varejo_amplo,
    greatest((0.2 * total - varejo_estrito) / 0.8, 0) as pontos_varejo_adicionais_estrito,
    greatest((0.2 * total - varejo_amplo) / 0.8, 0) as pontos_varejo_adicionais_amplo
from cen

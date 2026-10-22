-- Grão: tipo_resgate × período (PRE ou POS). Médias mensais de pontos_liquidos de mart_mix_absoluto_mensal.
-- PRE = 2026-02 a 2026-04 (3 meses). POS = 2026-06 a 2026-09 (4 meses).
-- Ficam de fora 2026-01 (outlier: 96,8% de aéreas) e 2026-05 (mês do lançamento do Pix, 27/05).
with periodos as (
    select
        mes,
        case
            when mes between '2026-02' and '2026-04' then 'PRE'
            when mes between '2026-06' and '2026-09' then 'POS'
        end as periodo
    from (select distinct mes from {{ ref('mart_mix_absoluto_mensal') }})
),

medias as (
    select
        m.tipo_resgate,
        p.periodo,
        count(*) as meses_no_periodo,
        avg(m.pontos_liquidos) as media_mensal_pontos_liquidos
    from {{ ref('mart_mix_absoluto_mensal') }} m
    join periodos p using (mes)
    where p.periodo is not null
    group by m.tipo_resgate, p.periodo
),

com_pre as (
    select
        *,
        max(media_mensal_pontos_liquidos) filter (where periodo = 'PRE') over (partition by tipo_resgate) as media_pre
    from medias
)

select
    tipo_resgate,
    periodo,
    meses_no_periodo,
    media_mensal_pontos_liquidos,
    case when periodo = 'POS' then media_mensal_pontos_liquidos - media_pre end as variacao_absoluta,
    case when periodo = 'POS' then (media_mensal_pontos_liquidos - media_pre) / nullif(media_pre, 0) end as variacao_pct
from com_pre

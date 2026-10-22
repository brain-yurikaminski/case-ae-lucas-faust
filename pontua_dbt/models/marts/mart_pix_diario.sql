-- Grão: 1 linha por dia (horário de Brasília), do primeiro ao último dia com resgate Pix ou evento da campanha.
-- Datas sempre em BRT (event_date_brt / data_brt), nunca UTC.
with pix as (
    select
        data_brt,
        count(*) as itens_pix,
        sum(pontos_brutos) as pontos_brutos_pix,
        sum(pontos_liquidos) as pontos_liquidos_pix
    from {{ ref('fct_resgates') }}
    where tipo_resgate = 'PIX'
    group by data_brt
),

camp as (
    select
        event_date_brt as data_brt,
        count(*) filter (where event_name = 'Notification Sent') as enviados,
        count(*) filter (where event_name = 'Notification Viewed') as abertos,
        count(*) filter (where event_name = 'Notification Clicked') as clicados,
        count(distinct user_id) filter (where event_name = 'Notification Sent') as usuarios_enviados,
        count(distinct user_id) filter (where event_name = 'Notification Viewed') as usuarios_abertos,
        count(distinct user_id) filter (where event_name = 'Notification Clicked') as usuarios_clicados
    from {{ ref('stg_crm_events') }}
    where campaign_id like 'CMP_LANCAMENTO_PIX%'
    group by event_date_brt
),

datas as (
    select data_brt from pix
    union
    select data_brt from camp
),

calendario as (
    select cast(d as date) as data_brt
    from generate_series(
        (select min(data_brt) from datas),
        (select max(data_brt) from datas),
        interval 1 day
    ) as t(d)
)

select
    c.data_brt,
    coalesce(p.itens_pix, 0) as itens_pix,
    coalesce(p.pontos_brutos_pix, 0) as pontos_brutos_pix,
    coalesce(p.pontos_liquidos_pix, 0) as pontos_liquidos_pix,
    coalesce(k.enviados, 0) as enviados,
    coalesce(k.abertos, 0) as abertos,
    coalesce(k.clicados, 0) as clicados,
    coalesce(k.usuarios_enviados, 0) as usuarios_enviados,
    coalesce(k.usuarios_abertos, 0) as usuarios_abertos,
    coalesce(k.usuarios_clicados, 0) as usuarios_clicados
from calendario c
left join pix p using (data_brt)
left join camp k using (data_brt)

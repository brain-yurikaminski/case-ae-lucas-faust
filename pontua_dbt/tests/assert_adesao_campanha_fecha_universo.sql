-- A soma de usuários dos 2 grupos = usuários distintos com resgate de 01/04 a 30/09/2026 em fct_resgates.
with u as (
    select count(distinct user_id) as usuarios
    from {{ ref('fct_resgates') }}
    where data_brt between date '2026-04-01' and date '2026-09-30'
),
g as (select sum(usuarios) as usuarios, sum(usuarios_resgataram_pix) as pix from {{ ref('mart_pix_adesao_campanha') }}),
p as (
    select count(distinct user_id) as pix
    from {{ ref('fct_resgates') }}
    where data_brt between date '2026-04-01' and date '2026-09-30' and tipo_resgate = 'PIX'
)

select u.usuarios as usuarios_universo, g.usuarios as usuarios_grupos, p.pix as pix_universo, g.pix as pix_grupos
from u, g, p
where u.usuarios <> g.usuarios or p.pix <> g.pix

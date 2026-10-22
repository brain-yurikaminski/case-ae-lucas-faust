-- mart_pix_diario e mart_pix_usuarios devem conter todos os itens Pix de fct_resgates.
with fct as (select count(*) as itens, sum(pontos_brutos) as pontos from {{ ref('fct_resgates') }} where tipo_resgate = 'PIX'),
dia as (select sum(itens_pix) as itens, sum(pontos_brutos_pix) as pontos from {{ ref('mart_pix_diario') }}),
usu as (select sum(itens_pix) as itens, sum(pontos_brutos_pix) as pontos from {{ ref('mart_pix_usuarios') }})

select fct.itens as itens_fct, dia.itens as itens_dia, usu.itens as itens_usuarios
from fct, dia, usu
where fct.itens <> dia.itens or fct.itens <> usu.itens or fct.pontos <> dia.pontos or fct.pontos <> usu.pontos

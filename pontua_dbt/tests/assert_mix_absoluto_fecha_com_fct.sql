-- Grão (mês, tipo_resgate) único; pontos e itens fecham com fct_resgates; reais_por_ponto do Pix na faixa contratada.
with mix as (select * from {{ ref('mart_mix_absoluto_mensal') }}),
fct as (select sum(pontos_liquidos) as pontos, count(*) as itens from {{ ref('fct_resgates') }})

select 'grao_duplicado' as teste, mes || '/' || tipo_resgate as detalhe
from mix group by mes, tipo_resgate having count(*) > 1
union all
select 'pontos_ou_itens_divergem', cast(sum(mix.pontos_liquidos) as varchar) || '/' || cast(sum(mix.itens) as varchar)
from mix, fct group by fct.pontos, fct.itens
having sum(mix.pontos_liquidos) <> fct.pontos or sum(mix.itens) <> fct.itens
union all
select 'pix_reais_por_ponto_fora_da_faixa', mes
from mix where tipo_resgate = 'PIX' and reais_por_ponto is not null and reais_por_ponto not between 0.0185 and 0.0195

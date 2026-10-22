-- Preço por ponto dos itens Pix APROVADO deve ficar entre 0,0185 e 0,0195 em todos os meses.
select mes, preco_por_ponto_aprovados
from {{ ref('mart_pix_preco_mensal') }}
where preco_por_ponto_aprovados is null
   or preco_por_ponto_aprovados not between 0.0185 and 0.0195

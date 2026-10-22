-- Soma dos pontos_liquidos de todos os meses = 320.027.439 (mesmo total da reconciliação com o ledger).
select sum(pontos_liquidos_total) as total
from {{ ref('mart_metas_mensal') }}
having sum(pontos_liquidos_total) <> 320027439

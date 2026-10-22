select order_item_id, pontos_liquidos
from {{ ref('fct_resgates') }}
where pontos_liquidos < 0

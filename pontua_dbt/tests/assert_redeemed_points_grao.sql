-- Grão de redeemed_points: (order_item_id, account_id, movement_type) deve ser único.
select order_item_id, account_id, movement_type, count(*) as linhas
from {{ ref('stg_redeemed_points') }}
group by 1, 2, 3
having count(*) > 1

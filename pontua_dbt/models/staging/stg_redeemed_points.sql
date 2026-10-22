select
    cast(order_item_id as bigint) as order_item_id,
    cast(account_id as bigint) as account_id,
    cast(movement_type as varchar) as movement_type,
    cast(points as bigint) as points
from {{ source('dados', 'redeemed_points') }}

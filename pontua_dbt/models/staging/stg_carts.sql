select
    cast(cart_id as bigint) as cart_id,
    cast(user_id as bigint) as user_id,
    cast(channel as varchar) as channel
from {{ source('dados', 'carts') }}

-- user_id de orders é 100% vazio e foi descartado de propósito: o usuário vem de carts.
select
    cast(order_id as bigint) as order_id,
    cast(cart_id as bigint) as cart_id,
    cast(status as varchar) as status,
    cast(created_at as timestamptz) as created_at,
    cast(status_updated_at as timestamptz) as status_updated_at
from {{ source('dados', 'orders') }}

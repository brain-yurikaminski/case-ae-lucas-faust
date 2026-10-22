select
    cast(order_item_id as bigint) as order_item_id,
    cast(order_id as bigint) as order_id,
    cast(created_at as timestamptz) as created_at,
    cast(status as varchar) as status,
    cast(product_type as varchar) as product_type,
    cast(supplier_name as varchar) as supplier_name,
    cast(supplier_responsible as varchar) as supplier_responsible,
    cast(category_macro as varchar) as category_macro,
    cast(paid_points as bigint) as paid_points,
    cast(paid_currency as double) as paid_currency,
    cast(product_value as double) as product_value,
    cast(refunded_points as bigint) as refunded_points,
    cast(quantity as bigint) as quantity
from {{ source('dados', 'order_items') }}

select
    cast(movement_id as bigint) as movement_id,
    cast(user_id as bigint) as user_id,
    cast(account_id as bigint) as account_id,
    cast(operation_code as bigint) as operation_code,
    cast(points as bigint) as points,
    cast(movement_at as timestamptz) as movement_at,
    cast(valid_until as date) as valid_until
from {{ source('dados', 'points_ledger') }}

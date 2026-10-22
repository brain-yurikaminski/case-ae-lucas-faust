select
    cast(account_id as bigint) as account_id,
    cast(user_id as bigint) as user_id,
    cast(card_class as varchar) as card_class,
    cast(card_flag as varchar) as card_flag,
    cast(created_at as timestamptz) as created_at,
    cast(is_most_recent as boolean) as is_most_recent
from {{ source('dados', 'cards') }}

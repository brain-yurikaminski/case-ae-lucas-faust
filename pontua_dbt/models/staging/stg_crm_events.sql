-- event_ts do CRM não tem fuso; está em UTC (provado cruzando 'Order Approved' com orders.created_at).
with base as (
    select
        cast(event_ts as timestamp) as event_ts_naive,
        cast(user_id as bigint) as user_id,
        cast(device_id as varchar) as device_id,
        cast(event_name as varchar) as event_name,
        cast(campaign_type as varchar) as campaign_type,
        cast(campaign_id as varchar) as campaign_id,
        cast(control_group as varchar) as control_group,
        cast(event_properties as varchar) as event_properties
    from {{ source('dados', 'crm_events') }}
)

select
    timezone('UTC', event_ts_naive) as event_ts_utc,
    timezone('America/Sao_Paulo', timezone('UTC', event_ts_naive)) as event_ts_brt,
    cast(timezone('America/Sao_Paulo', timezone('UTC', event_ts_naive)) as date) as event_date_brt,
    user_id,
    device_id,
    event_name,
    campaign_type,
    campaign_id,
    control_group,
    json_extract_string(event_properties::json, '$.campaign_name') as campaign_name,
    json_extract_string(event_properties::json, '$.platform') as platform,
    json_extract_string(event_properties::json, '$.link') as link,
    json_extract_string(event_properties::json, '$.reason') as reason,
    cast(json_extract_string(event_properties::json, '$.open_count') as integer) as open_count,
    event_properties
from base

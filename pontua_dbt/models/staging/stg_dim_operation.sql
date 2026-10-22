select
    cast(operation_code as bigint) as operation_code,
    cast(operation_name as varchar) as operation_name,
    cast(direction as varchar) as direction
from {{ source('dados', 'dim_operation') }}

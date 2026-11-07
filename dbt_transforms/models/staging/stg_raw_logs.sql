-- Only the six columns present in every environment. The streaming table also has
-- cpu/memory columns, but the seeded one historically did not, so we do not depend on them.
select
    cast(timestamp as timestamp) as timestamp,
    service_name,
    log_level,
    cast(http_status as integer) as http_status,
    cast(response_ms as {{ type_double() }}) as response_ms,
    cast(estimated_cost_usd as {{ type_double() }}) as estimated_cost_usd
from {{ source('cloudpulse', 'raw_logs') }}

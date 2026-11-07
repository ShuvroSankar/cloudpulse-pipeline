-- Rows an on-call engineer should look at (same thresholds as sql/queries/cost_anomalies.sql).
select
    timestamp,
    service_name,
    http_status,
    estimated_cost_usd,
    cost_z_score,
    case
        when cost_z_score >= 3.0 then 'CRITICAL'
        when cost_z_score >= 2.0 then 'WARNING'
    end as severity
from {{ ref('log_observability_enriched') }}
where cost_z_score >= 2.0

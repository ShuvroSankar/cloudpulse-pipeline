-- One row per service: the numbers behind the Executive FinOps dashboard.
select
    service_name,
    count(*) as total_requests,
    round(avg(response_ms), 2) as avg_latency_ms,
    max(service_p95_ms) as p95_latency_ms,
    round(max(response_ms), 2) as max_latency_ms,
    round(sum(estimated_cost_usd), 6) as total_cost_usd,
    round(sum(wasted_cost_usd), 6) as wasted_cost_usd,
    round(sum(estimated_cost_usd) / count(*) * 1000.0, 4) as unit_cost_per_1k_req_usd,
    round(100.0 * sum(case when is_server_error then 1 else 0 end) / count(*), 2) as server_error_rate_pct,
    sum(case when is_cost_anomaly then 1 else 0 end) as cost_anomaly_count,
    sum(case when service_health_status = 'CRITICAL' then 1 else 0 end) as critical_count
from {{ ref('log_observability_enriched') }}
group by service_name

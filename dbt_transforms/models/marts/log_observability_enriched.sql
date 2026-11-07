-- Per-request enrichment: wasted spend, unit cost, p95 tail, rolling z-score, health status.
-- Mirrors sql/bigquery/log_observability_enriched.sql, but runs on DuckDB and BigQuery.
with metrics as (
    select
        timestamp,
        service_name,
        log_level,
        http_status,
        response_ms,
        estimated_cost_usd,
        case when http_status >= 500 then estimated_cost_usd else 0.0 end as wasted_cost_usd,
        (http_status >= 400) as is_error,
        (http_status >= 500) as is_server_error,
        {{ p95_over('response_ms', 'service_name') }} as service_p95_ms,
        avg(estimated_cost_usd) over w50 as rolling_cost_mean,
        stddev_samp(estimated_cost_usd) over w50 as rolling_cost_std,
        sum(estimated_cost_usd) over w50 as rolling_50_req_cost_usd
    from {{ ref('stg_raw_logs') }}
    window w50 as (
        partition by service_name
        order by timestamp
        rows between 49 preceding and current row
    )
)

select
    timestamp,
    service_name,
    log_level,
    http_status,
    response_ms,
    round(service_p95_ms, 2) as service_p95_ms,
    estimated_cost_usd,
    round(wasted_cost_usd, 6) as wasted_cost_usd,
    round(estimated_cost_usd * 1000.0, 4) as cost_per_1k_req_usd,
    round((rolling_50_req_cost_usd / 50.0) * 1000.0, 4) as rolling_unit_cost_per_1k_req_usd,
    is_error,
    is_server_error,
    (response_ms > service_p95_ms) as is_latency_tail,
    round({{ safe_div('estimated_cost_usd - rolling_cost_mean', 'rolling_cost_std') }}, 2) as cost_z_score,
    (estimated_cost_usd > (rolling_cost_mean + 3 * ifnull(rolling_cost_std, 0))) as is_cost_anomaly,
    case
        when estimated_cost_usd > (rolling_cost_mean + 3 * ifnull(rolling_cost_std, 0)) and is_server_error then 'CRITICAL'
        when estimated_cost_usd > (rolling_cost_mean + 3 * ifnull(rolling_cost_std, 0)) or response_ms > service_p95_ms then 'WARNING'
        else 'HEALTHY'
    end as service_health_status
from metrics

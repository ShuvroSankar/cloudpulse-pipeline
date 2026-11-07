select * from {{ ref('service_health_summary') }}
where p95_latency_ms > max_latency_ms

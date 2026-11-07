select * from {{ ref('log_observability_enriched') }}
where service_health_status = 'CRITICAL' and not is_server_error

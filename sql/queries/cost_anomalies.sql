SELECT
    timestamp,
    service_name,
    http_status,
    estimated_cost_usd,
    cost_z_score,
    CASE
        WHEN cost_z_score >= 3.0 THEN 'CRITICAL'
        WHEN cost_z_score >= 2.0 THEN 'WARNING'
        ELSE 'NORMAL'
    END AS severity
FROM log_observability_enriched
WHERE cost_z_score >= 2.0
ORDER BY timestamp DESC;

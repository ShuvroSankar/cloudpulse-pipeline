SELECT
    service_name,
    COUNT(*) AS total_requests,
    ROUND(AVG(response_ms), 2) AS avg_latency_ms,
    ROUND(QUANTILE_CONT(response_ms, 0.95), 2) AS p95_latency_ms,
    ROUND(MAX(response_ms), 2) AS max_latency_ms
FROM raw_logs
GROUP BY service_name
ORDER BY p95_latency_ms DESC;

CREATE OR REPLACE VIEW `cloudpulse-finops-4321.cloudpulse_finops.log_observability_enriched` AS
WITH metrics AS (
    SELECT
        timestamp,
        service_name,
        log_level,
        http_status,
        response_ms,
        estimated_cost_usd,
        PERCENTILE_CONT(response_ms, 0.95) OVER (PARTITION BY service_name) AS service_p95_ms,
        AVG(estimated_cost_usd) OVER (
            PARTITION BY service_name 
            ORDER BY timestamp 
            ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
        ) AS rolling_cost_mean,
        STDDEV_SAMP(estimated_cost_usd) OVER (
            PARTITION BY service_name 
            ORDER BY timestamp 
            ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
        ) AS rolling_cost_std
    FROM `cloudpulse-finops-4321.cloudpulse_finops.raw_logs`
)
SELECT
    timestamp,
    service_name,
    log_level,
    http_status,
    response_ms,
    ROUND(service_p95_ms, 2) AS service_p95_ms,
    estimated_cost_usd,
    (response_ms > service_p95_ms) AS is_latency_tail,
    ROUND(SAFE_DIVIDE(estimated_cost_usd - rolling_cost_mean, rolling_cost_std), 2) AS cost_z_score,
    (estimated_cost_usd > (rolling_cost_mean + 3 * IFNULL(rolling_cost_std, 0))) AS is_cost_anomaly
FROM metrics;

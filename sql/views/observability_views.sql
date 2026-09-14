CREATE VIEW IF NOT EXISTS log_observability_enriched AS
WITH metrics AS (
	SELECT
		timestamp,
		service_name,
		log_level,
		http_status,
		response_ms,
		estimated_cost_usd,
		QUANTILE_CONT(response_ms, 0.95) OVER w_service AS service_p95_ms,
		QUANTILE_CONT(response_ms, 0.99) OVER w_service AS service_p99_ms,
		AVG(estimated_cost_usd) OVER w_service AS rolling_cost_mean,
		STDDEV_SAMP(estimated_cost_usd) OVER w_service_sliding AS rolling_cost_std
	FROM raw_logs
	WINDOW
		w_service AS (PARTITION BY service_name),
		w_service_sliding AS (
			PARTITION BY service_name
			ORDER BY timestamp
			ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
		)
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
		ROUND((estimated_cost_usd - rolling_cost_mean) / NULLIF(rolling_cost_std, 0), 2) AS cost_z_score,
		(estimated_cost_usd > (rolling_cost_mean + 3 * NULLIF(rolling_cost_std, 0))) AS is_cost_anomaly
	FROM metrics;


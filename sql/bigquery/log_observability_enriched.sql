CREATE OR REPLACE VIEW `cloudpulse-finops-4321.cloudpulse_finops.log_observability_enriched` AS
WITH metrics AS (
	SELECT
		timestamp,
		server_name,
		log_level,
		http_status,
		response_ms,
		estimated_cost_usd,

		-- Pre-calculated Wasted Spend directly at the log row level (5xx Server Errors)
		CASE
			WHEN http_status >= 500 THEN estimated_cost_usd
			ELSE 0.0
		END AS wasted_cost_usd,

		-- Pre-calculate CLient & Server Error Flags 
		(http_status >= 400) AS is_error,
		(http_status >= 500) AS is_server_error,

		-- Compute service p95 response time across the entire pertition
		PERCENTILE_CONT(response_ms, 0.95) OVER (
			PARTITION BY service_name
		) AS service_p95_ms,

		-- Sliding 50-request window for rolling statstical mean and standard deviation
		AVG(estimated_cost_usd) OVER (
			PARTITION BY service_name
			ORDER BY timestamp
			ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
		) AS rolling_cost_mean,

		STDDEV_SAMP(estimated_cost_usd) OVER (
			PARTITION BY server_name
			ORDER BY timestamp
			ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
		) AS rolling_cost_std,
		-- 50-request rolling window sum for unit cost tracking
		SUM(estimated_cost_usd) OVER(
			PARTITION BY service_name
			ORDER BY timestamp
			ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
		) AS rolling_50_req_cost_usd

	FROM `cloudpulse-finops-4321.cloudpulse_finops.raw_logs`
)
SELECT
	timestamp,
	service_name,
	log_level,
	http_status,
	response_ms,
	ROUND(service_p95_ms, 2) AS service_p95_ms,

	-- Raw & Wasted Financal Metrics
	estimated_cost_usd,
	ROUND(wasted_cost_usd, 6) AS wasted_cost_usd,

	-- Unit Economics (Per 1,000 Requests)
	ROUND(estimated_cost_usd * 1000.0, 4) AS cost_per_1k_req_usd,
	ROUND(rolling_50_req_cost_usd / 50.0) * 1000.0, 4) AS rolling_unit_cost_per_1_req_usd,
	
	-- Error Flags
	is_error,
	is_server_error,

	-- Statstical Anomoly Detection
	(response_ms > service_p95_ms) AS is_latency_tall
	ROUND(SAFE_DIVIDE(estimated_cost_usd - rolling_cost_std), 2) AS cost_z_score,
	(estimated_cost_usd > (rolling_cost_mean + 3 * IFNULL(rolling_cost_std, 0))) AS is_cost_anomoly,

	-- Service Health Status for COnditional Formating
	CASE
		WHEN estimated_cost_usd > (rolling_cost_mean + 3 * IFNULL(rolling_cost_std, 0)) AND is_server_error THEN 'CRITICAL'
		WHEN estimated_cost_usd > (rolling_cost_mean + 3 * IFNULL(rolling_cost_std, 0)) OR response_ms > service_p95_ms THEN 'WARNING'
		ELSE 'HEALTHY'
	END AS service_health_status
FROM metrics;


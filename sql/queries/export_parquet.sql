-- Export enriched observability data to Hive-partitioned Parquet files

COPY(
	SELECT
		*,
		CAST(timestamp AS DATE) AS log_date
	FROM log_observability_enriched
) TO 'data/exports/observability_enriched'
(
	FORMAT PARQUET,
	PARTITION_BY (service_name, log_date),
	OVERWRITE_OR_IGNORE
);


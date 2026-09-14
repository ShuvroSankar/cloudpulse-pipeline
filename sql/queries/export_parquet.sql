-- Export enriched observability logs to a single Parquet file
COPY (
    SELECT * FROM log_observability_enriched
) TO 'data/exports/raw_logs/logs.parquet'
(
    FORMAT PARQUET
);

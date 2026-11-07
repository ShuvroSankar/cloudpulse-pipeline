-- Export enriched observability logs to a single Parquet file
COPY (
    SELECT * FROM raw_logs
) TO 'data/exports/raw_logs/logs.parquet'
(
    FORMAT PARQUET
);

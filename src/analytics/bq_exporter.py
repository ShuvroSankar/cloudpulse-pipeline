import sys
from pathlib import Path
from google.cloud import bigquery

class BigQueryPipelineExporter:
    """Syncs DuckDB Parquet exports into Google BigQuery."""

    def __init__(self, project_id: str = "cloudpulse-finops-4321", dataset_id: str = "cloudpulse_finops"):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=project_id)
        self.dataset_ref = f"{project_id}.{dataset_id}"

    def sync_parquet_to_bigquery(self, parquet_dir: str = "data/exports/raw_logs"):
        table_ref = f"{self.dataset_ref}.raw_logs"

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            autodetect=True,
        )

        parquet_files = [str(p) for p in Path(parquet_dir).rglob("*.parquet")]

        if not parquet_files:
            print(f"No Parquet files found in '{parquet_dir}'. Run Parquet export first.")
            return False

        print(f"Uploading {len(parquet_files)} Parquet file(s) to BigQuery table {table_ref}...")

        for file_path in parquet_files:
            with open(file_path, "rb") as source_file:
                load_job = self.client.load_table_from_file(
                    source_file, table_ref, job_config=job_config
                )
                load_job.result()

        print(f"Successfully loaded data into BigQuery: {table_ref}")
        return True

    def create_enriched_view(self, sql_file: str = "sql/bigquery/log_observability_enriched.sql"):
        sql_path = Path(sql_file)
        if not sql_path.exists():
            print(f"SQL file not found: {sql_file}")
            return

        with open(sql_path, "r") as f:
            query = f.read()

        query_job = self.client.query(query)
        query_job.result()
        print(f"Created BigQuery View: {self.dataset_ref}.log_observability_enriched")


if __name__ == "__main__":
    print("Starting BigQuery Pipeline Exporter...")
    try:
        exporter = BigQueryPipelineExporter()
        if exporter.sync_parquet_to_bigquery():
            exporter.create_enriched_view()
        print("BigQuery Sync Completed Successfully.")
    except Exception as e:
        print(f"Error during BigQuery sync: {e}", file=sys.stderr)

import duckdb
from pathlib import Path
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option('display.width', 1000)


class CloudPulseAnalytics:
    """Executes analytical quries and manages DuckDB views."""
    def __init__(self, db_path: str = "cloudpulse.db", sql_dir: str = "sql"):
        self.db_path = db_path
        self.sql_dir = Path(sql_dir)
        self.conn = duckdb.connect(db_path)
        self._register_views()
    
    def _register_views(self):
        """ Loads and executes all SQL view definations in sql/views."""
        views_dir = self.sql_dir / "views"
        if views_dir.exists():
            for view_file in sorted(views_dir.glob("*.sql")):
                with open(view_file,"r") as f:
                    self.conn.execute(f.read())
            print("[Analytics Engine] DuckDB views successfully registered.")

    def run_query_from_file(self, query_filename: str):
        """Reads a .sql file from sql/queries and returns pandas Dataframe."""
        query_path = self.sql_dir / "queries" / query_filename
        with open(query_path, "r") as f:
            sql = f.read()
        return self.conn.execute(sql).df()

    def execute_export_from_file(self, query_filename: str = "export_parquet.sql"):
        """Executes a COPY statement stored in sql/queries to export data."""
        query_path = self.sql_dir / "queries" / query_filename
        with open(query_path, "r") as f:
            sql = f.read()
        self.conn.execute(sql)
        print(f"[Parquet Export] Successfully executed export query from '{query_path}'")

if __name__ == "__main__":
    analytics = CloudPulseAnalytics()

    print("\n [P95 Latency Metrics]:")
    print(analytics.run_query_from_file("p95_latency.sql"))

    print("\n [Cost Anomalies]:")
    print(analytics.run_query_from_file("cost_anomalies.sql"))

    print("\n [Exporting Parquet Data]:")
    analytics.execute_export_from_file("export_parquet.sql")


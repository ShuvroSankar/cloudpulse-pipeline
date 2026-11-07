"""Shared fixtures. Every test uses a throwaway DuckDB file, never the real cloudpulse.db."""
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = REPO_ROOT / "sql"

RAW_LOGS_DDL = """
CREATE TABLE raw_logs (
    timestamp TIMESTAMP,
    service_name VARCHAR,
    log_level VARCHAR,
    http_status INTEGER,
    response_ms DOUBLE,
    estimated_cost_usd DOUBLE
)
"""


def build_rows(n_normal: int = 60, spike_cost: float = 0.009):
    """Deterministic rows: two services with flat cost/latency, plus one cost spike at the end of
    'payment-gateway' (a 5xx with a very high cost and latency)."""
    start = datetime(2026, 9, 14, 0, 0, 0)
    rows = []
    for i in range(n_normal):
        # tiny alternation so std-dev is non-zero but small
        cost = 0.0004 + (0.00001 if i % 2 else 0.0)
        rows.append((start + timedelta(minutes=i), "payment-gateway", "INFO", 200, 100.0 + i, cost))
        rows.append((start + timedelta(minutes=i), "auth-service", "INFO", 200, 50.0 + i, cost))
    rows.append((start + timedelta(minutes=n_normal), "payment-gateway", "ERROR", 503, 4000.0, spike_cost))
    return rows


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def seeded_db(db_path):
    conn = duckdb.connect(db_path)
    conn.execute(RAW_LOGS_DDL)
    conn.executemany("INSERT INTO raw_logs VALUES (?,?,?,?,?,?)", build_rows())
    conn.close()
    return db_path


@pytest.fixture
def sql_dir():
    return str(SQL_DIR)

"""Runs the dbt project against a throwaway DuckDB and cross-checks it against the hand-written view."""
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from src.analytics.metrics_engine import CloudPulseAnalytics

pytestmark = pytest.mark.dbt
dbt_mod = pytest.importorskip("dbt.cli.main")

DBT_DIR = Path(__file__).resolve().parents[1] / "dbt_transforms"


@pytest.fixture
def built_db(seeded_db, sql_dir, tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUDPULSE_DB_PATH", seeded_db)
    # make sure the DuckDB view exists too, for the parity check
    CloudPulseAnalytics(db_path=seeded_db, sql_dir=sql_dir).conn.close()
    res = dbt_mod.dbtRunner().invoke([
        "build", "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR), "--target", "dev",
        "--target-path", str(tmp_path / "target"), "--log-path", str(tmp_path / "logs"),
    ])
    assert res.success, f"dbt build failed: {res.exception or [r.message for r in res.result if r.status in ('error','fail')]}"
    return seeded_db


def test_dbt_build_succeeds_and_creates_marts(built_db):
    conn = duckdb.connect(built_db)
    tables = {r[0] for r in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main_marts'").fetchall()}
    assert {"log_observability_enriched", "service_health_summary", "cost_anomalies"} <= tables


def test_dbt_enriched_matches_handwritten_duckdb_view(built_db):
    conn = duckdb.connect(built_db)
    cols = "timestamp, service_name, response_ms, service_p95_ms, is_latency_tail, cost_z_score, is_cost_anomaly"
    order = "ORDER BY service_name, timestamp, response_ms"
    view = conn.execute(f"SELECT {cols} FROM main.log_observability_enriched {order}").df()
    mart = conn.execute(f"SELECT {cols} FROM main_marts.log_observability_enriched {order}").df()
    pd.testing.assert_frame_equal(view, mart, check_dtype=False)


def test_dbt_summary_totals_agree_with_raw_logs(built_db):
    conn = duckdb.connect(built_db)
    raw_n, raw_cost = conn.execute("SELECT COUNT(*), SUM(estimated_cost_usd) FROM raw_logs").fetchone()
    n, cost = conn.execute("SELECT SUM(total_requests), SUM(total_cost_usd) FROM main_marts.service_health_summary").fetchone()
    assert n == raw_n and cost == pytest.approx(raw_cost, rel=1e-4)


def test_dbt_flags_the_planted_spike_as_critical(built_db):
    conn = duckdb.connect(built_db)
    row = conn.execute("SELECT service_name, severity FROM main_marts.cost_anomalies ORDER BY cost_z_score DESC LIMIT 1").fetchone()
    assert row == ("payment-gateway", "CRITICAL")

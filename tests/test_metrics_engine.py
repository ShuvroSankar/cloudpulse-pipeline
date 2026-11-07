import duckdb
import pytest

from src.analytics.metrics_engine import CloudPulseAnalytics


@pytest.fixture
def engine(seeded_db, sql_dir):
    return CloudPulseAnalytics(db_path=seeded_db, sql_dir=sql_dir)


def test_views_are_registered(engine):
    assert engine.conn.execute("SELECT COUNT(*) FROM log_observability_enriched").fetchone()[0] == 121


def test_view_registration_is_idempotent_and_replaces(seeded_db, sql_dir):
    CloudPulseAnalytics(db_path=seeded_db, sql_dir=sql_dir).conn.close()
    CloudPulseAnalytics(db_path=seeded_db, sql_dir=sql_dir)  # second init must not raise


def test_p95_latency_query_matches_pandas(engine):
    df = engine.run_query_from_file("p95_latency.sql").set_index("service_name")
    raw = engine.conn.execute("SELECT service_name, response_ms FROM raw_logs").df()
    for svc, grp in raw.groupby("service_name"):
        assert df.loc[svc, "total_requests"] == len(grp)
        assert df.loc[svc, "p95_latency_ms"] == round(grp["response_ms"].quantile(0.95), 2)
        assert df.loc[svc, "max_latency_ms"] == grp["response_ms"].max()


def test_p95_results_sorted_descending(engine):
    p95 = engine.run_query_from_file("p95_latency.sql")["p95_latency_ms"].tolist()
    assert p95 == sorted(p95, reverse=True)


def test_cost_anomaly_query_flags_the_planted_spike(engine):
    df = engine.run_query_from_file("cost_anomalies.sql")
    assert len(df) >= 1
    top = df.iloc[0]
    assert top["service_name"] == "payment-gateway"
    assert top["http_status"] == 503
    assert top["severity"] == "CRITICAL"
    assert (df["cost_z_score"] >= 2.0).all()


def test_flat_service_has_no_cost_anomalies(engine):
    df = engine.run_query_from_file("cost_anomalies.sql")
    assert "auth-service" not in set(df["service_name"])


def test_is_cost_anomaly_flag_agrees_with_z_score(engine):
    rows = engine.conn.execute(
        "SELECT cost_z_score, is_cost_anomaly FROM log_observability_enriched WHERE is_cost_anomaly"
    ).fetchall()
    assert rows and all(z is not None and z > 3 for z, _ in rows)


def test_latency_tail_is_about_five_percent_of_each_service(engine):
    df = engine.conn.execute(
        "SELECT service_name, AVG(is_latency_tail::INT) AS share FROM log_observability_enriched GROUP BY 1"
    ).df()
    assert df["share"].between(0.01, 0.10).all()


def test_parquet_export_creates_missing_directory(seeded_db, sql_dir, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # export SQL uses a relative path: data/exports/raw_logs/logs.parquet
    eng = CloudPulseAnalytics(db_path=seeded_db, sql_dir=sql_dir)
    eng.execute_export_from_file("export_parquet.sql")
    out = tmp_path / "data/exports/raw_logs/logs.parquet"
    assert out.exists()
    n = duckdb.connect().execute(f"SELECT COUNT(*) FROM read_parquet('{out}')").fetchone()[0]
    assert n == 121


def test_rolling_mean_and_std_use_the_same_window(engine):
    """regression: mean used the whole partition while std used a 50-row window, which produced
    z-scores around -28 for perfectly flat services."""
    z = engine.conn.execute(
        "SELECT MIN(cost_z_score) FROM log_observability_enriched WHERE service_name = 'auth-service'"
    ).fetchone()[0]
    assert z > -3

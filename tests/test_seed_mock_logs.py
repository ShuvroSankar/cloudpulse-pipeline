import duckdb

from src.data.seed_mock_logs import generate_mock_logs
from src.ingestion.stream_consumer import DuckDBIngestionEngine


def _cols(path):
    conn = duckdb.connect(path, read_only=True)
    try:
        return [r[0] for r in conn.execute("DESCRIBE raw_logs").fetchall()]
    finally:
        conn.close()


def test_seeds_requested_row_count(db_path):
    generate_mock_logs(db_path=db_path, total_logs=500, seed=42)
    conn = duckdb.connect(db_path, read_only=True)
    assert conn.execute("SELECT COUNT(*) FROM raw_logs").fetchone()[0] == 500


def test_seed_is_deterministic_with_seed(tmp_path):
    a, b = str(tmp_path / "a.db"), str(tmp_path / "b.db")
    generate_mock_logs(db_path=a, total_logs=100, seed=7)
    generate_mock_logs(db_path=b, total_logs=100, seed=7)
    q = "SELECT service_name, http_status, response_ms FROM raw_logs ORDER BY timestamp, service_name, response_ms"
    ra = duckdb.connect(a, read_only=True).execute(q).fetchall()
    rb = duckdb.connect(b, read_only=True).execute(q).fetchall()
    assert ra == rb


def test_reseeding_replaces_instead_of_appending(db_path):
    generate_mock_logs(db_path=db_path, total_logs=50, seed=1)
    generate_mock_logs(db_path=db_path, total_logs=50, seed=1)
    conn = duckdb.connect(db_path, read_only=True)
    assert conn.execute("SELECT COUNT(*) FROM raw_logs").fetchone()[0] == 50


def test_spikes_are_server_errors_with_high_latency(db_path):
    generate_mock_logs(db_path=db_path, total_logs=3000, seed=3)
    conn = duckdb.connect(db_path, read_only=True)
    bad_spikes = conn.execute(
        "SELECT COUNT(*) FROM raw_logs WHERE response_ms >= 1500 AND http_status < 500"
    ).fetchone()[0]
    assert bad_spikes == 0
    assert conn.execute("SELECT COUNT(*) FROM raw_logs WHERE http_status >= 500").fetchone()[0] > 0


def test_seeded_schema_matches_streaming_schema(tmp_path):
    """regression: seeder made 6 columns, consumer inserts 8, so streaming into a seeded DB crashed."""
    seeded, streamed = str(tmp_path / "s.db"), str(tmp_path / "t.db")
    generate_mock_logs(db_path=seeded, total_logs=10, seed=1)
    eng = DuckDBIngestionEngine(db_path=streamed)
    eng.conn.close()
    assert _cols(seeded) == _cols(streamed)


def test_consumer_can_append_to_a_seeded_db(db_path):
    generate_mock_logs(db_path=db_path, total_logs=10, seed=1)
    eng = DuckDBIngestionEngine(db_path=db_path, batch_size=1)
    eng._flush_buffer([{
        "timestamp": "2026-09-14T00:00:00+00:00", "service_name": "auth-service", "log_level": "INFO",
        "http_status": 200, "response_ms": 12.0, "cpu_utilization": 20.0,
        "memory_utilization": 40.0, "estimated_cost_usd": 0.0002,
    }])
    assert eng.conn.execute("SELECT COUNT(*) FROM raw_logs").fetchone()[0] == 11

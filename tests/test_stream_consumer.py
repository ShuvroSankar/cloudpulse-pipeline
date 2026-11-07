import asyncio
import json

from src.generator.log_producer import inject_anomalies
from src.ingestion.stream_consumer import DuckDBIngestionEngine


def _payload(i=0, service="auth-service"):
    e = inject_anomalies(service)
    e["timestamp"] = f"2026-09-14T00:00:{i % 60:02d}+00:00"
    return json.dumps(e)


def _count(engine):
    return engine.conn.execute("SELECT COUNT(*) FROM raw_logs").fetchone()[0]


def test_schema_created_with_eight_columns(db_path):
    eng = DuckDBIngestionEngine(db_path=db_path)
    cols = [r[0] for r in eng.conn.execute("DESCRIBE raw_logs").fetchall()]
    assert cols == [
        "timestamp", "service_name", "log_level", "http_status", "response_ms",
        "cpu_utilization", "memory_utilization", "estimated_cost_usd",
    ]


def test_schema_init_is_idempotent(db_path):
    DuckDBIngestionEngine(db_path=db_path).conn.close()
    DuckDBIngestionEngine(db_path=db_path)  # must not raise


def test_flush_buffer_inserts_every_row(db_path):
    eng = DuckDBIngestionEngine(db_path=db_path)
    eng._flush_buffer([json.loads(_payload(i)) for i in range(7)])
    assert _count(eng) == 7


def test_consume_flushes_in_batches_then_drains_on_cancel(db_path):
    async def run():
        eng = DuckDBIngestionEngine(db_path=db_path, batch_size=5)
        q: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(eng.consume_and_buffer(q))
        for i in range(12):
            await q.put(_payload(i))
        await asyncio.sleep(0.1)
        assert _count(eng) == 10  # two full batches flushed, 2 rows still buffered
        task.cancel()
        await task
        return eng

    eng = asyncio.run(run())
    assert _count(eng) == 12  # leftover buffer flushed on graceful shutdown


def test_query_live_metrics_aggregates_per_service(db_path):
    eng = DuckDBIngestionEngine(db_path=db_path)
    eng._flush_buffer([json.loads(_payload(i, "auth-service")) for i in range(3)]
                      + [json.loads(_payload(i, "inventory-api")) for i in range(2)])
    df = eng.query_live_metrics().set_index("service_name")
    assert df.loc["auth-service", "total_requests"] == 3
    assert df.loc["inventory-api", "total_requests"] == 2
    assert (df["total_cost_usd"] > 0).all()

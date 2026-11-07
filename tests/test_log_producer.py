import asyncio
import json
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.generator.log_producer import (
    HTTP_STATUSES,
    LOG_LEVEL_MAP,
    SERVICES,
    LogEvent,
    inject_anomalies,
    stream_logs,
)

EVENT_FIELDS = {
    "service_name", "log_level", "http_status", "response_ms",
    "cpu_utilization", "memory_utilization", "estimated_cost_usd",
}


def test_every_status_has_a_log_level():
    assert set(HTTP_STATUSES) <= set(LOG_LEVEL_MAP)


def test_service_names_are_spelled_consistently():
    # regression: producer used to say "recomendation-engine" while the seeder said "recommendation"
    assert "recommendation-engine" in SERVICES
    assert "recomendation-engine" not in SERVICES


def test_normal_event_shape_and_ranges():
    with patch("src.generator.log_producer.random.random", return_value=0.99):
        for _ in range(200):
            e = inject_anomalies("auth-service")
            assert set(e) == EVENT_FIELDS
            assert 10.0 <= e["response_ms"] <= 200.0
            assert 15.0 <= e["cpu_utilization"] <= 65.0
            assert e["http_status"] in HTTP_STATUSES
            assert e["log_level"] == LOG_LEVEL_MAP[e["http_status"]]


def test_anomaly_event_is_slow_hot_and_a_server_error():
    with patch("src.generator.log_producer.random.random", return_value=0.0):
        for _ in range(200):
            e = inject_anomalies("auth-service")
            assert e["http_status"] in (500, 503)
            assert 800.0 <= e["response_ms"] <= 3500.0
            assert e["cpu_utilization"] >= 85.0
            assert e["log_level"] in ("ERROR", "CRITICAL")


def test_cost_formula():
    e = inject_anomalies("auth-service")
    expected = round(
        e["cpu_utilization"] * 0.000005 + e["memory_utilization"] * 0.000002 + e["response_ms"] * 0.000001, 6
    )
    assert e["estimated_cost_usd"] == expected


def test_anomaly_rate_is_roughly_five_percent():
    import random
    random.seed(1)
    n = 20_000
    slow = sum(inject_anomalies("x")["response_ms"] >= 800 for _ in range(n))
    assert 0.03 < slow / n < 0.07


def test_log_event_defaults_timestamp_and_validates():
    e = LogEvent(**inject_anomalies("auth-service"))
    assert e.timestamp  # default_factory fills it in
    with pytest.raises(ValidationError):
        LogEvent(service_name="x", log_level="INFO", http_status="not-a-number",
                 response_ms=1.0, cpu_utilization=1.0, memory_utilization=1.0, estimated_cost_usd=0.1)


def test_stream_logs_pushes_valid_json_and_stops_cleanly():
    async def run():
        q: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(stream_logs(target_queue=q, delay_seconds=0.001))
        await asyncio.sleep(0.05)
        task.cancel()
        await task  # producer swallows CancelledError, so this must not raise
        return q

    q = asyncio.run(run())
    assert q.qsize() > 0
    payload = json.loads(q.get_nowait())
    assert EVENT_FIELDS <= set(payload) and "timestamp" in payload

import asyncio
import json
import random
from datetime import datetime, timezone
from typing import Dict, Any
from pydantic import BaseModel, Field

class LogEvent(BaseModel):
	"""Pydantic model defining the strict schema for generated log events"""
	timestamp: str = Field(default_factory = lambda: datetime.now(timezone.utc).isoformat())
	service_name: str
	log_level: str
	http_status: int
	response_ms: float
	cpu_utilization: float
	memory_utilization: float
	estimated_cost_usd: float

SERVICES = ["payment-gateway", "auth-service", "inventory-api", "recomendation-engine"]
HTTP_STATUSES = [200, 200, 200, 200, 201, 400, 404, 500, 503]
LOG_LEVEL_MAP = {
	200: "INFO",
	201: "INFO",
	400: "WARN",
	404: "WARN",
	500: "ERROR",
	503: "CRITICAL"
}

def inject_anomalies(service: str) -> Dict[str, Any]:
	"""Simulates real-world traffic patterns, including sudden latency spikes and errors."""
# 5% chance to trigger a massive latency/error anomaly
	is_anomaly = random.random() <0.05
	if is_anomaly:
		status = random.choice([500, 503])
		response_ms =round(random.uniform(800.0, 3500.0), 2)
		cpu = round(random.uniform(85.0, 99.9), 1)
		mem = round(random.uniform(30.0, 70.0),1)
	else:
		status = random.choice(HTTP_STATUSES)
		response_ms = round(random.uniform(10.0, 200.0), 2)
		cpu = round(random.uniform(15.0, 65.0), 1)
		mem = round(random.uniform(30.0, 70.0), 1)
	log_level = LOG_LEVEL_MAP.get(status, "INFO")
	# Calculate synthetic micro-cost (FinOps metric: cost per API request based on CPU/RAM usage)
	cost = round((cpu * 0.000005) + (mem * 0.000002) + (response_ms * 0.000001),6)
	return {
		"service_name": service,
		"log_level": log_level,
		"http_status": status,
		"response_ms": response_ms,
		"cpu_utilization": cpu,
		"memory_utilization": mem,
		"estimated_cost_usd": cost,
	}
async def stream_logs(target_queue: asyncio.Queue = None, delay_seconds: float = 0.1):
# Async generator that continiously yields o pushes LogEvent payloads.
# - target_queue: Optional asyncio.Queue for internal memory streaming to local consumers.
# - delay_seconds: Controls throughput (e.g., 0.1s = 10 events/sec, 0.01s = 100 events/sec).
	print(f"[Producer] Starting log stream generation (Interval: {delay_seconds}s)...")

	try:
		while True:
			service = random.choice(SERVICES)
			raw_event = inject_anomalies(service)
			
			# Instantiate & validate via Pydantic
			event = LogEvent(**raw_event)
			json_payload = event.model_dump_json()
			if target_queue:
				await target_queue.put(json_payload)
			else:
			# Direct stdout printing if running standalone script
				print(json_payload)
			await asyncio.sleep(delay_seconds)

	except asyncio.CancelledError:
		print("\n [Producer] Stream generation stopped gracefully.")

if __name__ == "__main__":
	# Test execution: Run standalone loop printing to stdout
	try:
		asyncio.run(stream_logs(delay_seconds = 0.2))
	except KeyboardInterrupt:
		pass

		

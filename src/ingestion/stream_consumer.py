#!/usr/bin/env python3

import asyncio
import json
import duckdb
from typing import List, Dict, Any
from src.generator.log_producer import stream_logs

class DuckDBIngestionEngine:
    """Buffers streaming log records into memory and flushes them into a DuckDB analytical database."""
    def __init__(self, db_path: str =  "cloudpulse.db", batch_size: int = 20):
        self.db_path = db_path
        self.batch_size = batch_size
        self.conn = duckdb.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        """ Creates the raw_logs table schemaif it does not already exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_logs (
                timestamp TIMESTAMP,
                service_name VARCHAR,
                log_level VARCHAR,
                http_status INTEGER,
                response_ms DOUBLE,
                cpu_utilization DOUBLE,
                memory_utilization DOUBLE,
                estimated_cost_usd DOUBLE
                )
            """)
    async def consume_and_buffer(self, queue: asyncio.Queue):
        """
        Continiously read from the queue, accumulates records, 
        and triggers a batch write when threshhold is reached.
        """
        buffer: List[Dict[str, Any]] = []
        print(f"[Ingestion Engine] Activate queue consumer started (Batch Size Threshold: {self.batch_size})...")
        try:
            while True:
                # Non-blocking fetch from asyncio Queue
                raw_payload = await queue.get()
                log_data = json.loads(raw_payload)
                buffer.append(log_data)

                #Batch write condition
                if len(buffer) >= self.batch_size:
                    self._flush_buffer(buffer)
                    buffer.clear()
                queue.task_done()

        except asyncio.CancelledError:
            # Dain remaining items in queue on graceful shutdown
            if buffer:
                self._flush_buffer(buffer)
            print(f"[Ingestion Engine] Consumer stopped successfully.")
    def _flush_buffer(self, batch: List[Dict[str, Any]]):
        """ Converts raw dicts into SQL touples 
        and writes to DuckDB using vectorized bulk inserts."""
        records = [
                (
                    item["timestamp"],
                    item["service_name"],
                    item["log_level"],
                    item["http_status"],
                    item["response_ms"],
                    item["cpu_utilization"],
                    item["memory_utilization"],
                    item["estimated_cost_usd"],
                    )
                for item in batch
                ]
        self.conn.executemany("""
        INSERT INTO raw_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, records)
        print(f"[DuckDB] Bulk-inserted batch of {len(records)} into table 'raw_logs'.")

    def query_live_metrics(self):
        """ Returns aggregate computr metrics across ingested services."""
        return self.conn.execute("""
            SELECT
                service_name,
                COUNT(*) as total_requests,
                ROUND(AVG(response_ms), 2) as avg_latency_ms,
                ROUND(SUM(estimated_cost_usd), 6) as total_cost_usd
            FROM raw_logs
            GROUP BY service_name
            ORDER BY total_cost_usd DESC
            """).df()
async def main():
    """Intregation launcher linking generator and
    ingestion engine via shared Queue."""
    shared_queue = asyncio.Queue()
    ingestor = DuckDBIngestionEngine(batch_size=15)
    # Concurrently run both tasks on the event loop
    producer_task = asyncio.create_task(stream_logs(target_queue=shared_queue, delay_seconds=0.05))
    consumer_task = asyncio.create_task(ingestor.consume_and_buffer(queue=shared_queue))

    try:
        await asyncio.sleep(5)
            
    finally:
        producer_task.cancel()
        consumer_task.cancel()
        await asyncio.gather(producer_task, consumer_task, return_exceptions=True)
        print("\n [Analytics Snapshot] DuckDB Aggregated Metrics:")
        print(ingestor.query_live_metrics())

if __name__ == "__main__":
     asyncio.run(main())




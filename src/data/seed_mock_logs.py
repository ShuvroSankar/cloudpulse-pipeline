import duckdb
import random
from datetime import datetime, timedelta

def generate_mock_logs(db_path: str = 'cloudpulse.db', hours: int = 24, total_logs = 8000):
    print(f"Genareting {total_logs} servability logs accross the last {hours} hours...")
    conn = duckdb.connect(db_path)

    # Re-create raw_logs table
    conn.execute("DROP TABLE IF EXISTS raw_logs;")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS raw_logs (
        timestamp TIMESTAMP,
        service_name VARCHAR,
        log_level VARCHAR,
        http_status INT,
        response_ms DOUBLE,
        estimated_cost_usd DOUBLE
        );
        TRUNCATE TABLE raw_logs;
    """)
    services = ["auth-service", "payment-gateway", "inventory-api", "recommendation-engine", "notification-service"]
    end_time = datetime.now()
    log_levels = ['INFO', 'WARN', 'ERROR']
    start_time = end_time - timedelta(hours = hours)
    time_step = (end_time - start_time)/total_logs


    records = []
    current_time = start_time

    for i in range(total_logs):
        current_time += time_step + timedelta(seconds = random.uniform(-1,1))
        service = random.choice(services)

        # Inject Intentional anomaly ay specific intervals
        is_spike  = random.random() < 0.03  # #% chance in anaomoly

        if is_spike:
            log_level = "ERROR"
            http_status = random.choice([500, 502, 503])
            response_ms = round(random.uniform(1500, 4500), 2)
            estimated_cost_usd = round(random.uniform(0.003, 0.009), 6)

        else:
            log_level = random.choices(log_levels, weights = [85, 10, 5])[0]
            http_status = 200 if log_level != "ERROR" else 400
            response_ms = round(random.uniform(20,350),2)
            estimated_cost_usd = round(random.uniform(0.0001, 0.0008),6)

        records.append((current_time, service, log_level, http_status, response_ms, estimated_cost_usd))

    conn.executemany("""
        INSERT INTO raw_logs VALUES(?,?,?,?,?,?)
    """, records)

    count = conn.execute("SELECT COUNT(*) FROM raw_logs").fetchone()[0]
    print(f"Successfully seeded {count} rows into DuckDB table 'raw_logs'.")
    conn.close()
if __name__ == "__main__":
    generate_mock_logs()


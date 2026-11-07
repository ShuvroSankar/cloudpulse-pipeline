# CloudPulse: Real-Time FinOps &amp; Infrastructure Observability Pipeline

[Python 3.10+](https://www.python.org/)  
[Google BigQuery](https://cloud.google.com/bigquery)  
[Looker Studio](https://lookerstudio.google.com/)  
[License: MIT](https://opensource.org/licenses/MIT)

[**→ Open the live Looker Studio dashboard**](https://datastudio.google.com/reporting/a6356cf1-1906-4d59-87ae-0177e4be0534)

**CloudPulse** is an end-to-end FinOps and infrastructure observability platform designed to bridge the gap between engineering latency metrics and cloud cost anomalies.

CloudPulse consumes synthetic asynchronous log streams, applies statistical anomaly detection (Z-score modeling and P95 latency profiling) in BigQuery, and serves dual-persona BI dashboards in Looker Studio — enabling real-time identification of wasted cloud spend, microservice degradation, and unit economics across distributed architectures.

---

## Executive &amp; SRE Dashboards

### Page 1: Executive FinOps &amp; Spend Overview

*Designed for engineering management and FinOps leaders to monitor cloud spend, unit economics and HTTP 5xx costs.*

Page 1 - Executive FinOps Overview

**Key Highlights:**

- **Total Spend &amp; Unit Economics:** `Total Cost ($)` alongside `Unit Cost per 1k Requests ($)`.
- **Wasted Spend Engine:** direct financial loss from failed server requests (HTTP 5xx).
- **Service Health Categorization:** `HEALTHY`, `WARNING`, `CRITICAL` status per request.
- **Cost vs. Latency Correlation:** dual-axis time series correlating response-time degradation with cost spikes.

### Page 2: SRE Incident Triage

*Designed for on-call engineers and SREs to isolate rogue microservices, HTTP error spikes and statistical cost anomalies.*



**Key Highlights:**

- **Statistical Anomaly Detection:** rolling 50-request cost z-score per service — hard-flagged at z &gt; 3 for incident triage.
- **P95 Latency Profiling:** per-service p95 and tail-latency flags (`is_latency_tail`).
- **Error Triage:** client (4xx) vs server (5xx) error flags to separate user mistakes from outages.

---

## Architecture

Architecture

```
log_producer (async) -> asyncio.Queue -> stream_consumer -> DuckDB raw_logs
                                                              |
                         sql/views + dbt_transforms  <--------+
                                                              |
                                  Parquet export -> BigQuery -> Looker Studio
```

## Getting Started

Requires Python **3.10+** (BigQuery sync needs GCP credentials; everything else runs locally on DuckDB).

```bash
pip install -e ".[dev]"      # or: make install
make seed                    # create cloudpulse.db with 8,000 mock logs
make analytics               # views, p95, anomalies, parquet export
make dbt                     # build + test dbt models on DuckDB
make test                    # full test suite
```

Stream live instead of seeding: `python -m src.ingestion.stream_consumer`.

## dbt models (`dbt_transforms/`)


| Model                        | Purpose                                                               |
| ---------------------------- | --------------------------------------------------------------------- |
| `stg_raw_logs`               | typed, minimal view over `raw_logs`                                   |
| `log_observability_enriched` | per-request wasted spend, unit cost, p95 tail, z-score, health status |
| `service_health_summary`     | per-service roll-up for the executive page                            |
| `cost_anomalies`             | anomaly rows with cost z-score &gt;= 2                                |


Two-tier thresholding: incident triage flags fire at **z &gt; 3**, while `cost_anomalies` casts a wider net at **z ≥ 2** for exploration and dashboard drill-down.

The same models run on DuckDB (`--target dev`, default) and BigQuery (`--target prod`); the few  
functions that differ between the two engines live in `macros/cross_db.sql`.

## Testing

`pytest` runs unit tests for the generator, consumer, seeder, SQL analytics and BigQuery exporter  
(mocked), plus an integration test that builds the dbt project and checks it matches the hand-written  
DuckDB view. Use `make test-fast` to skip the dbt integration tests.

## License

MIT

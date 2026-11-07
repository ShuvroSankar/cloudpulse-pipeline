-- Singular test: returns offending rows; the test fails if any come back.
select * from {{ ref('stg_raw_logs') }}
where response_ms < 0 or estimated_cost_usd < 0

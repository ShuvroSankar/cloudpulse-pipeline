#!/usr/bin/env bash
# Run from the repo root:  bash scripts/verify_setup.sh
# Checks that the CloudPulse updates were applied correctly. Never touches your real cloudpulse.db.
cd "$(dirname "$0")/.." || exit 1
pass=0; fail=0
ok()   { echo "  PASS  $1"; pass=$((pass+1)); }
bad()  { echo "  FAIL  $1"; fail=$((fail+1)); }
has()  { grep -q -- "$2" "$1" 2>/dev/null; }

echo "1. Required files"
for f in Makefile .gitignore .github/workflows/ci.yml pyproject.toml README.md \
  dbt_transforms/dbt_project.yml dbt_transforms/profiles.yml dbt_transforms/macros/cross_db.sql \
  dbt_transforms/models/staging/stg_raw_logs.sql dbt_transforms/models/staging/_sources.yml \
  dbt_transforms/models/marts/log_observability_enriched.sql dbt_transforms/models/marts/service_health_summary.sql \
  dbt_transforms/models/marts/cost_anomalies.sql dbt_transforms/models/marts/_marts.yml \
  tests/conftest.py tests/test_log_producer.py tests/test_stream_consumer.py tests/test_seed_mock_logs.py \
  tests/test_metrics_engine.py tests/test_bq_exporter.py tests/test_dbt_models.py; do
  [ -f "$f" ] && ok "$f" || bad "missing: $f"
done
n=$(ls dbt_transforms/tests/*.sql 2>/dev/null | wc -l); [ "$n" -ge 4 ] && ok "dbt singular tests ($n)" || bad "expected 4 dbt singular tests, found $n"

echo "2. Bug fixes actually applied"
! has src/generator/log_producer.py "recomendation" && ok "service name typo fixed" || bad "log_producer.py still says 'recomendation-engine'"
has src/data/seed_mock_logs.py "cpu_utilization" && has src/data/seed_mock_logs.py "VALUES(?,?,?,?,?,?,?,?)" && ok "seeder writes 8 columns" || bad "seed_mock_logs.py is the old 6-column version"
has sql/views/observability_views.sql "CREATE OR REPLACE VIEW" && ok "view uses CREATE OR REPLACE" || bad "view still uses IF NOT EXISTS"
has sql/views/observability_views.sql "AVG(estimated_cost_usd) OVER w_service_sliding AS rolling_cost_mean" && ok "rolling mean uses sliding window" || bad "view still has the mismatched mean/std windows (wrong z-scores)"
! has sql/views/observability_views.sql "3 \* NULLIF" && ok "anomaly flag uses IFNULL" || bad "view still uses NULLIF(std,0) for is_cost_anomaly"
has src/analytics/metrics_engine.py "mkdir" && ok "export creates missing directory" || bad "metrics_engine.py not updated (export dir)"
has src/analytics/bq_exporter.py "WRITE_APPEND" && ok "BigQuery loader appends after first file" || bad "bq_exporter.py not updated (WRITE_TRUNCATE bug)"
has pyproject.toml "dbt-duckdb" && has pyproject.toml "pytest.ini_options" && ok "pyproject has dbt-duckdb + pytest config" || bad "pyproject.toml not updated"
git check-ignore -q cloudpulse.db 2>/dev/null && ok "cloudpulse.db is git-ignored" || echo "  WARN  cloudpulse.db not git-ignored (or not a git repo)"

echo "3. Environment"
python - <<'PY' 2>/dev/null && ok "python deps import (duckdb, pydantic, pytest, dbt, bigquery)" || bad "missing deps: run  pip install -e '.[dev]'"
import duckdb, pydantic, pytest, dbt.cli.main, google.cloud.bigquery
PY

echo "4. Lint"
if command -v ruff >/dev/null; then ruff check --config pyproject.toml src tests >/dev/null 2>&1 && ok "ruff clean" || bad "ruff errors (run: ruff check src tests)"; else echo "  SKIP  ruff not installed"; fi

echo "5. Test suite (unit + dbt integration, on temp databases)"
out=$(python -m pytest -q -p no:cacheprovider 2>&1); echo "$out" | tail -1 | sed 's/^/        /'
echo "$out" | tail -1 | grep -q "passed" && ! echo "$out" | tail -1 | grep -q "failed\|error" && ok "pytest all green" || { bad "pytest has failures"; echo "$out" | grep -E "^(FAILED|ERROR)" | sed 's/ - .*//;s/^/        /'; }

echo "6. dbt build on a COPY of your real database"
if [ -f cloudpulse.db ]; then
  tmp=$(mktemp -d)/copy.db; cp cloudpulse.db "$tmp"
  cols=$(python -c "import duckdb;print(len(duckdb.connect('$tmp',read_only=True).execute('describe raw_logs').fetchall()))" 2>/dev/null)
  [ "$cols" = "8" ] && ok "cloudpulse.db raw_logs has 8 columns" || echo "  WARN  cloudpulse.db raw_logs has ${cols:-?} columns (old schema). Run: make seed"
  (cd dbt_transforms && CLOUDPULSE_DB_PATH="$tmp" dbt build --profiles-dir . --target dev --target-path "$(dirname $tmp)/t" --log-path "$(dirname $tmp)/l" 2>&1 | grep -E "Done\. PASS" | sed 's/\x1b\[[0-9;]*m//g;s/^[0-9:]* *//;s/^/        /')
  (cd dbt_transforms && CLOUDPULSE_DB_PATH="$tmp" dbt build --profiles-dir . --target dev --target-path "$(dirname $tmp)/t" --log-path "$(dirname $tmp)/l" >/dev/null 2>&1) && ok "dbt build + 20 data tests pass on your data" || bad "dbt build failed on your data"
else
  echo "  SKIP  no cloudpulse.db here (run: make seed)"
fi

echo; echo "Result: $pass passed, $fail failed"; [ "$fail" -eq 0 ] && echo "Everything is updated correctly." || echo "Fix the FAIL lines above, then re-run."
exit $fail

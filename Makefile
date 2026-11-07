.PHONY: verify install seed analytics export dbt test test-fast lint clean

verify:
	bash scripts/verify_setup.sh

install:
	python -m pip install -e ".[dev]"

seed:
	python -m src.data.seed_mock_logs

analytics:
	python -m src.analytics.metrics_engine

export:
	python -m src.analytics.bq_exporter

dbt:
	cd dbt_transforms && dbt build --profiles-dir . --target $(or $(TARGET),dev)

test:
	pytest

test-fast:
	pytest -m "not dbt"

lint:
	ruff check src tests

clean:
	rm -rf dbt_transforms/target dbt_transforms/logs .pytest_cache


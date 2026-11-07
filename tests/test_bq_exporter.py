from unittest.mock import patch

import pytest

pytest.importorskip("google.cloud.bigquery")
from google.cloud import bigquery

from src.analytics.bq_exporter import BigQueryPipelineExporter


@pytest.fixture
def exporter():
    with patch("src.analytics.bq_exporter.bigquery.Client") as client_cls:
        exp = BigQueryPipelineExporter(project_id="p", dataset_id="d")
        exp.client = client_cls.return_value
        yield exp


def test_no_parquet_files_returns_false(exporter, tmp_path):
    assert exporter.sync_parquet_to_bigquery(str(tmp_path)) is False
    exporter.client.load_table_from_file.assert_not_called()


def test_multiple_files_truncate_once_then_append(exporter, tmp_path):
    for name in ("a.parquet", "b.parquet", "c.parquet"):
        (tmp_path / name).write_bytes(b"PAR1")
    assert exporter.sync_parquet_to_bigquery(str(tmp_path)) is True
    calls = exporter.client.load_table_from_file.call_args_list
    dispositions = [c.kwargs["job_config"].write_disposition for c in calls]
    assert dispositions == [
        bigquery.WriteDisposition.WRITE_TRUNCATE,
        bigquery.WriteDisposition.WRITE_APPEND,
        bigquery.WriteDisposition.WRITE_APPEND,
    ]
    assert all(c.args[1] == "p.d.raw_logs" for c in calls)


def test_create_enriched_view_runs_sql_file(exporter, tmp_path):
    f = tmp_path / "v.sql"
    f.write_text("SELECT 1")
    exporter.create_enriched_view(str(f))
    exporter.client.query.assert_called_once_with("SELECT 1")


def test_create_enriched_view_missing_file_is_a_noop(exporter, tmp_path):
    exporter.create_enriched_view(str(tmp_path / "nope.sql"))
    exporter.client.query.assert_not_called()

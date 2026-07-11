import os
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any

from app.core.config import settings


BIGQUERY_TYPE_MAP = {
    "INTEGER": "INT64",
    "FLOAT": "FLOAT64",
    "BOOLEAN": "BOOL",
    "DATE": "DATE",
    "DATETIME": "DATETIME",
    "STRING": "STRING",
}


def _get_bigquery_module():
    try:
        from google.cloud import bigquery
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-bigquery is not installed. Install backend requirements before using BigQuery loading."
        ) from exc

    return bigquery


def get_bigquery_client():
    bigquery = _get_bigquery_module()
    project = settings.GCP_PROJECT_ID or None
    if settings.GOOGLE_APPLICATION_CREDENTIALS:
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", settings.GOOGLE_APPLICATION_CREDENTIALS)
    return bigquery.Client(project=project)


def _resolve_project_id(client) -> str:
    project_id = settings.GCP_PROJECT_ID or getattr(client, "project", None)
    if not project_id:
        raise ValueError("GCP_PROJECT_ID must be configured for BigQuery loading")
    return project_id


def _resolve_dataset_id() -> str:
    dataset_id = settings.BIGQUERY_DATASET_ID
    if not dataset_id:
        raise ValueError("BIGQUERY_DATASET_ID must be configured for BigQuery loading")
    return dataset_id


def ensure_bigquery_dataset(client):
    bigquery = _get_bigquery_module()
    project_id = _resolve_project_id(client)
    dataset_id = _resolve_dataset_id()
    full_dataset_id = f"{project_id}.{dataset_id}"

    try:
        return client.get_dataset(full_dataset_id)
    except Exception as exc:
        if exc.__class__.__name__ != "NotFound":
            raise

    dataset = bigquery.Dataset(full_dataset_id)
    dataset.location = "US"
    return client.create_dataset(dataset, exists_ok=True)


def sanitize_table_name(name: str, dataset_id: int) -> str:
    normalized = name.lower().strip()
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")

    if not normalized:
        normalized = "dataset"

    prefix = f"dataset_{dataset_id}_"
    max_suffix_length = max(1, 1024 - len(prefix))
    suffix = normalized[:max_suffix_length].rstrip("_") or "dataset"
    return f"{prefix}{suffix}"


def map_to_bigquery_type(data_type: str) -> str:
    return BIGQUERY_TYPE_MAP.get((data_type or "").upper(), "STRING")


def build_bigquery_schema(dataset_columns):
    bigquery = _get_bigquery_module()
    return [
        bigquery.SchemaField(
            column.name,
            map_to_bigquery_type(column.data_type),
            mode="NULLABLE" if column.nullable else "REQUIRED",
        )
        for column in sorted(dataset_columns, key=lambda column: column.ordinal_position)
    ]


def load_csv_to_bigquery(dataset, dataset_columns) -> dict[str, Any]:
    if not dataset.storage_path:
        raise ValueError("Dataset does not have an uploaded CSV file")

    csv_path = Path(dataset.storage_path)
    if not csv_path.exists():
        raise ValueError("Uploaded CSV file was not found on local storage")

    columns = list(dataset_columns)
    if not columns:
        raise ValueError("Dataset does not have a detected schema")

    bigquery = _get_bigquery_module()
    client = get_bigquery_client()
    ensure_bigquery_dataset(client)

    project_id = _resolve_project_id(client)
    dataset_id = _resolve_dataset_id()
    table_name = sanitize_table_name(dataset.name, dataset.id)
    table_id = f"{project_id}.{dataset_id}.{table_name}"
    schema = build_bigquery_schema(columns)

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=False,
        allow_quoted_newlines=True,
    )

    with csv_path.open("rb") as csv_file:
        load_job = client.load_table_from_file(csv_file, table_id, job_config=job_config)

    load_job.result()
    table = client.get_table(table_id)

    return {
        "bigquery_table_id": table_id,
        "job_id": getattr(load_job, "job_id", None),
        "row_count": getattr(table, "num_rows", None),
        "column_count": len(schema),
    }


def get_bigquery_table_info(bigquery_table_id: str) -> dict[str, Any]:
    client = get_bigquery_client()
    table = client.get_table(bigquery_table_id)

    return {
        "table_id": bigquery_table_id,
        "num_rows": getattr(table, "num_rows", None),
        "num_bytes": getattr(table, "num_bytes", None),
        "schema": [
            {"name": field.name, "type": field.field_type, "mode": field.mode}
            for field in getattr(table, "schema", [])
        ],
    }


@dataclass(frozen=True)
class QueryDryRunResult:
    total_bytes_processed: int | None
    job_id: str | None
    location: str | None
    estimate_accuracy: str | None = None


def run_query_dry_run(sql: str) -> QueryDryRunResult:
    bigquery = _get_bigquery_module()
    client = get_bigquery_client()
    job_config = bigquery.QueryJobConfig(
        dry_run=True,
        use_query_cache=False,
        use_legacy_sql=False,
    )
    query_job = client.query(sql, job_config=job_config)
    return QueryDryRunResult(
        total_bytes_processed=getattr(query_job, "total_bytes_processed", None),
        job_id=getattr(query_job, "job_id", None),
        location=getattr(query_job, "location", None),
        estimate_accuracy=getattr(query_job, "estimated_bytes_processed_accuracy", None),
    )


@dataclass(frozen=True)
class QueryResultColumn:
    name: str
    field_type: str
    mode: str | None = None


@dataclass(frozen=True)
class QueryExecutionResult:
    job_id: str | None
    location: str | None
    total_bytes_processed: int | None
    total_bytes_billed: int | None
    cache_hit: bool | None
    columns: list[QueryResultColumn]
    rows: list[dict[str, Any]]
    result_truncated: bool


class BigQueryExecutionTimeout(TimeoutError):
    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message)
        self.job_id = job_id


def _row_to_mapping(row: Any, field_names: list[str]) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "items"):
        try:
            return dict(row.items())
        except Exception:
            pass
    if field_names:
        return {name: row[index] for index, name in enumerate(field_names)}
    return dict(row)


def execute_query(
    sql: str,
    maximum_bytes_billed: int,
    row_limit: int,
    timeout_seconds: int,
) -> QueryExecutionResult:
    bigquery = _get_bigquery_module()
    client = get_bigquery_client()
    job_config = bigquery.QueryJobConfig(
        use_legacy_sql=False,
        maximum_bytes_billed=maximum_bytes_billed,
        use_query_cache=True,
    )
    query_job = client.query(sql, job_config=job_config)

    try:
        row_iterator = query_job.result(timeout=timeout_seconds, max_results=row_limit + 1)
    except TimeoutError as exc:
        try:
            query_job.cancel()
        finally:
            raise BigQueryExecutionTimeout("The query timed out before completion.", getattr(query_job, "job_id", None)) from exc

    schema = list(getattr(row_iterator, "schema", None) or getattr(query_job, "schema", []) or [])
    columns = [
        QueryResultColumn(
            name=getattr(field, "name", ""),
            field_type=getattr(field, "field_type", getattr(field, "type", "")),
            mode=getattr(field, "mode", None),
        )
        for field in schema
    ]
    field_names = [column.name for column in columns]
    fetched_rows = [_row_to_mapping(row, field_names) for row in row_iterator]
    result_truncated = len(fetched_rows) > row_limit

    return QueryExecutionResult(
        job_id=getattr(query_job, "job_id", None),
        location=getattr(query_job, "location", None),
        total_bytes_processed=getattr(query_job, "total_bytes_processed", None),
        total_bytes_billed=getattr(query_job, "total_bytes_billed", None),
        cache_hit=getattr(query_job, "cache_hit", None),
        columns=columns,
        rows=fetched_rows[:row_limit],
        result_truncated=result_truncated,
    )

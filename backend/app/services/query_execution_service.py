import base64
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.query_request import QueryRequest
from app.services.bigquery_service import BigQueryExecutionTimeout, execute_query
from app.services.sql_validation_service import SQLValidatorInternalError, validate_generated_sql


class QueryExecutionRequestError(RuntimeError):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class QueryExecutionInternalError(RuntimeError):
    pass


def _add_audit_log(
    db: Session,
    user_id: int,
    action: str,
    query_request_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource_type="query_request",
            resource_id=str(query_request_id) if query_request_id is not None else None,
            details=details,
        )
    )


def _safe_error_message(exc: Exception) -> str:
    class_name = exc.__class__.__name__
    text = str(exc).lower()
    if "maximum bytes" in text or "maximum_bytes" in text or "billing tier" in text:
        return "The query exceeded the configured maximum bytes billed."
    if class_name in {"DefaultCredentialsError", "RefreshError"} or "credential" in text:
        return "Google Cloud credentials are not configured correctly."
    if class_name in {"Forbidden", "PermissionDenied"} or "permission" in text:
        return "The configured Google Cloud identity cannot execute BigQuery jobs."
    if class_name == "NotFound" or "not found" in text:
        return "The source table could not be found."
    if class_name == "BadRequest" or "invalid" in text or "unrecognized" in text:
        return "BigQuery execution failed."
    if "api" in text and "disabled" in text:
        return "The BigQuery API may be disabled for the configured project."
    if "location" in text:
        return "BigQuery could not execute the query because of a location mismatch."
    if "quota" in text:
        return "BigQuery could not execute the query because a quota limit was reached."
    if "network" in text or "connection" in text:
        return "BigQuery execution failed because of a network issue."
    return "BigQuery execution failed."


def _load_owned_query(db: Session, current_user_id: int, query_request_id: int) -> QueryRequest:
    query_request = db.query(QueryRequest).filter(QueryRequest.id == query_request_id, QueryRequest.user_id == current_user_id).first()
    if query_request is None:
        raise QueryExecutionRequestError("Query request not found", status.HTTP_404_NOT_FOUND)
    return query_request


def _load_owned_dataset(db: Session, current_user_id: int, query_request: QueryRequest) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == query_request.dataset_id, Dataset.owner_id == current_user_id).first()
    if dataset is None:
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Dataset not found", status_code=status.HTTP_404_NOT_FOUND, set_ineligible=True)
    return dataset


def _block_query(
    db: Session,
    current_user_id: int,
    query_request: QueryRequest,
    audit_action: str,
    detail: str,
    *,
    status_code: int = status.HTTP_409_CONFLICT,
    set_ineligible: bool = False,
) -> None:
    now = datetime.utcnow()
    query_request.execution_status = "blocked"
    query_request.execution_started_at = query_request.execution_started_at or now
    query_request.execution_completed_at = now
    query_request.execution_error = detail
    if set_ineligible:
        query_request.execution_eligible = False
    _add_audit_log(
        db,
        current_user_id,
        audit_action,
        query_request.id,
        {"dataset_id": query_request.dataset_id, "execution_status": "blocked", "error": detail},
    )
    db.commit()
    raise QueryExecutionRequestError(detail, status_code)


def _require_pre_execution_gates(db: Session, current_user_id: int, query_request: QueryRequest) -> None:
    if query_request.generation_status != "generated":
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Query generation must succeed before execution")
    if not query_request.generated_sql:
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Query request does not have generated SQL")
    if query_request.validation_status != "passed":
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Query must pass SQL safety validation before execution")
    if query_request.is_safe is not True:
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Query must be marked safe before execution")
    if query_request.dry_run_status != "passed":
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Query must pass BigQuery dry run before execution")
    if query_request.dry_run_valid is not True:
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "BigQuery dry run must be valid before execution")
    if query_request.bytes_limit_exceeded is not False:
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Query estimated bytes exceed the configured maximum bytes billed", set_ineligible=True)
    if query_request.execution_eligible is not True:
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Query is not eligible for execution")
    if query_request.estimated_bytes_processed is None:
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Query dry run must include an estimated bytes value", set_ineligible=True)
    if query_request.estimated_bytes_processed > settings.MAX_BYTES_BILLED:
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Query estimated bytes exceed the configured maximum bytes billed", set_ineligible=True)


def _require_dataset_context(db: Session, current_user_id: int, query_request: QueryRequest, dataset: Dataset) -> None:
    if dataset.status != "loaded":
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Dataset must be loaded into BigQuery before execution", set_ineligible=True)
    if not dataset.bigquery_table_id:
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Dataset does not have a BigQuery table ID", set_ineligible=True)
    if not query_request.generated_for_table_id:
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Query table context is missing; regenerate and revalidate the query", set_ineligible=True)
    if query_request.generated_for_table_id != dataset.bigquery_table_id:
        _block_query(db, current_user_id, query_request, "query.execution_blocked", "Dataset BigQuery table changed after generation; regenerate, revalidate, and dry run the query", set_ineligible=True)


def _revalidate_for_execution(db: Session, current_user_id: int, query_request: QueryRequest, dataset: Dataset) -> None:
    columns = (
        db.query(DatasetColumn)
        .filter(DatasetColumn.dataset_id == dataset.id)
        .order_by(DatasetColumn.ordinal_position)
        .all()
    )
    allowed_columns = [column.name for column in columns]
    try:
        result = validate_generated_sql(query_request.generated_sql or "", dataset.bigquery_table_id or "", allowed_columns)
    except SQLValidatorInternalError as exc:
        raise QueryExecutionInternalError("SQL validator failed during execution revalidation") from exc
    if not result.is_safe:
        _block_query(
            db,
            current_user_id,
            query_request,
            "query.execution_blocked",
            "Stored SQL no longer passes execution-time validation",
            set_ineligible=True,
        )


def _effective_row_limit(requested_row_limit: int | None) -> int:
    if requested_row_limit is None:
        return settings.QUERY_RESULT_ROW_LIMIT
    if requested_row_limit > settings.QUERY_RESULT_ROW_LIMIT:
        raise QueryExecutionRequestError("Requested row limit exceeds the configured server maximum")
    return requested_row_limit


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "items"):
        try:
            return {str(key): _json_safe(item) for key, item in value.items()}
        except Exception:
            pass
    return str(value)


def _safe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{str(key): _json_safe(value) for key, value in row.items()} for row in rows]


def _to_response(query_request: QueryRequest, row_limit: int | None = None) -> dict[str, Any]:
    return {
        "query_request_id": query_request.id,
        "dataset_id": query_request.dataset_id,
        "execution_status": query_request.execution_status,
        "execution_job_id": query_request.execution_job_id,
        "execution_location": query_request.execution_location,
        "execution_bytes_processed": query_request.execution_bytes_processed,
        "execution_bytes_billed": query_request.execution_bytes_billed,
        "execution_cache_hit": query_request.execution_cache_hit,
        "result_row_count": query_request.result_row_count or 0,
        "result_columns": query_request.result_columns or [],
        "result_rows": query_request.result_rows or [],
        "result_truncated": bool(query_request.result_truncated),
        "row_limit": row_limit or settings.QUERY_RESULT_ROW_LIMIT,
        "execution_error": query_request.execution_error,
        "execution_started_at": query_request.execution_started_at,
        "execution_completed_at": query_request.execution_completed_at,
        "executed_at": query_request.executed_at,
        "generated_sql": query_request.generated_sql or "",
    }


def execute_query_request(
    db: Session,
    current_user_id: int,
    query_request_id: int,
    requested_row_limit: int | None = None,
) -> dict[str, Any]:
    query_request = _load_owned_query(db, current_user_id, query_request_id)
    row_limit = _effective_row_limit(requested_row_limit)
    _require_pre_execution_gates(db, current_user_id, query_request)
    dataset = _load_owned_dataset(db, current_user_id, query_request)
    _require_dataset_context(db, current_user_id, query_request, dataset)
    _revalidate_for_execution(db, current_user_id, query_request, dataset)

    started_at = datetime.utcnow()
    query_request.execution_status = "running"
    query_request.execution_started_at = started_at
    query_request.execution_completed_at = None
    query_request.execution_error = None
    query_request.execution_job_id = None
    query_request.execution_location = None
    query_request.execution_bytes_processed = None
    query_request.execution_bytes_billed = None
    query_request.execution_cache_hit = None
    query_request.result_row_count = None
    query_request.result_columns = None
    query_request.result_rows = None
    query_request.result_truncated = None
    _add_audit_log(db, current_user_id, "query.execution_started", query_request.id, {"dataset_id": dataset.id, "row_limit": row_limit})
    db.commit()
    db.refresh(query_request)

    try:
        result = execute_query(
            query_request.generated_sql or "",
            maximum_bytes_billed=settings.MAX_BYTES_BILLED,
            row_limit=row_limit,
            timeout_seconds=settings.QUERY_TIMEOUT_SECONDS,
        )
        safe_rows = _safe_rows(result.rows)
        columns = [{"name": column.name, "field_type": column.field_type, "mode": column.mode} for column in result.columns]
        completed_at = datetime.utcnow()
        query_request.execution_status = "succeeded"
        query_request.execution_job_id = result.job_id
        query_request.execution_location = result.location
        query_request.execution_bytes_processed = result.total_bytes_processed
        query_request.execution_bytes_billed = result.total_bytes_billed
        query_request.execution_cache_hit = result.cache_hit
        query_request.result_columns = columns
        query_request.result_rows = safe_rows
        query_request.result_row_count = len(safe_rows)
        query_request.result_truncated = result.result_truncated
        query_request.execution_completed_at = completed_at
        query_request.executed_at = completed_at
        query_request.execution_error = None
        _add_audit_log(
            db,
            current_user_id,
            "query.execution_succeeded",
            query_request.id,
            {
                "dataset_id": dataset.id,
                "execution_job_id": result.job_id,
                "bytes_processed": result.total_bytes_processed,
                "bytes_billed": result.total_bytes_billed,
                "result_row_count": len(safe_rows),
                "result_truncated": result.result_truncated,
                "execution_status": "succeeded",
            },
        )
    except BigQueryExecutionTimeout as exc:
        completed_at = datetime.utcnow()
        query_request.execution_status = "timed_out"
        query_request.execution_job_id = exc.job_id
        query_request.execution_completed_at = completed_at
        query_request.execution_error = "The query timed out before completion."
        _add_audit_log(db, current_user_id, "query.execution_timed_out", query_request.id, {"dataset_id": dataset.id, "execution_job_id": exc.job_id})
    except Exception as exc:
        completed_at = datetime.utcnow()
        class_name = exc.__class__.__name__
        is_internal = class_name in {"DefaultCredentialsError", "RefreshError"}
        query_request.execution_status = "error" if is_internal else "failed"
        query_request.execution_completed_at = completed_at
        query_request.execution_error = _safe_error_message(exc)
        _add_audit_log(
            db,
            current_user_id,
            "query.execution_error" if is_internal else "query.execution_failed",
            query_request.id,
            {"dataset_id": dataset.id, "execution_status": query_request.execution_status, "error": query_request.execution_error},
        )
    db.commit()
    db.refresh(query_request)
    return _to_response(query_request, row_limit)


def get_query_execution(db: Session, current_user_id: int, query_request_id: int) -> dict[str, Any]:
    query_request = _load_owned_query(db, current_user_id, query_request_id)
    if query_request.execution_status == "not_executed":
        raise QueryExecutionRequestError("Query has not been executed")
    return _to_response(query_request)

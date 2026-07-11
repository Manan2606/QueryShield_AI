from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import status
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.dataset import Dataset
from app.models.query_request import QueryRequest
from app.services.query_dry_run_service import bytes_to_gib, bytes_to_mib, bytes_to_tib

QUERY_STATUS_FILTERS = {
    "generation_status": {"pending", "generated", "failed"},
    "validation_status": {"not_validated", "validating", "passed", "failed", "error"},
    "dry_run_status": {"not_run", "running", "passed", "blocked", "failed", "error"},
    "execution_status": {"not_executed", "running", "succeeded", "failed", "blocked", "timed_out", "error"},
}
MAX_HISTORY_LIMIT = 100
MAX_AUDIT_LIMIT = 100


class QueryHistoryRequestError(RuntimeError):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _validate_limit(limit: int, max_limit: int) -> int:
    if limit <= 0:
        raise QueryHistoryRequestError("Limit must be greater than 0")
    return min(limit, max_limit)


def _validate_sort_order(sort_order: str) -> str:
    normalized = sort_order.lower()
    if normalized not in {"asc", "desc"}:
        raise QueryHistoryRequestError("sort_order must be 'asc' or 'desc'")
    return normalized


def _format_decimal(value: Decimal | None) -> str | None:
    return f"{value:.6f}" if value is not None else None


def _sql_preview(sql: str | None, length: int = 180) -> str | None:
    if not sql:
        return None
    normalized = " ".join(sql.split())
    return normalized if len(normalized) <= length else normalized[: length - 3] + "..."


def _dataset_name(dataset: Dataset | None) -> str | None:
    return dataset.name if dataset is not None else None


def _history_item(query_request: QueryRequest) -> dict[str, Any]:
    return {
        "id": query_request.id,
        "dataset_id": query_request.dataset_id,
        "dataset_name": _dataset_name(query_request.dataset),
        "question": query_request.natural_language_question,
        "generated_sql_preview": _sql_preview(query_request.generated_sql),
        "generation_status": query_request.generation_status,
        "validation_status": query_request.validation_status,
        "is_safe": query_request.is_safe,
        "dry_run_status": query_request.dry_run_status,
        "estimated_bytes_processed": query_request.estimated_bytes_processed,
        "estimated_cost": _format_decimal(query_request.estimated_cost),
        "estimated_cost_currency": query_request.estimated_cost_currency,
        "bytes_limit_exceeded": query_request.bytes_limit_exceeded,
        "execution_eligible": query_request.execution_eligible,
        "execution_status": query_request.execution_status,
        "result_row_count": query_request.result_row_count,
        "result_truncated": query_request.result_truncated,
        "created_at": query_request.created_at,
        "validated_at": query_request.validated_at,
        "dry_run_at": query_request.dry_run_at,
        "executed_at": query_request.executed_at,
    }


def list_query_history(
    db: Session,
    current_user_id: int,
    *,
    skip: int = 0,
    limit: int = 25,
    dataset_id: int | None = None,
    generation_status: str | None = None,
    validation_status: str | None = None,
    dry_run_status: str | None = None,
    execution_status: str | None = None,
    is_safe: bool | None = None,
    execution_eligible: bool | None = None,
    search: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort_order: str = "desc",
) -> dict[str, Any]:
    if skip < 0:
        raise QueryHistoryRequestError("skip must be greater than or equal to 0")
    effective_limit = _validate_limit(limit, MAX_HISTORY_LIMIT)
    order = _validate_sort_order(sort_order)

    filters = {
        "generation_status": generation_status,
        "validation_status": validation_status,
        "dry_run_status": dry_run_status,
        "execution_status": execution_status,
    }
    for field, value in filters.items():
        if value is not None and value not in QUERY_STATUS_FILTERS[field]:
            raise QueryHistoryRequestError(f"Invalid {field} filter")

    query = db.query(QueryRequest).outerjoin(Dataset, QueryRequest.dataset_id == Dataset.id).filter(QueryRequest.user_id == current_user_id)
    if dataset_id is not None:
        query = query.filter(QueryRequest.dataset_id == dataset_id)
    if generation_status is not None:
        query = query.filter(QueryRequest.generation_status == generation_status)
    if validation_status is not None:
        query = query.filter(QueryRequest.validation_status == validation_status)
    if dry_run_status is not None:
        query = query.filter(QueryRequest.dry_run_status == dry_run_status)
    if execution_status is not None:
        query = query.filter(QueryRequest.execution_status == execution_status)
    if is_safe is not None:
        query = query.filter(QueryRequest.is_safe.is_(is_safe))
    if execution_eligible is not None:
        query = query.filter(QueryRequest.execution_eligible.is_(execution_eligible))
    if created_from is not None:
        query = query.filter(QueryRequest.created_at >= created_from)
    if created_to is not None:
        query = query.filter(QueryRequest.created_at <= created_to)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(QueryRequest.natural_language_question.ilike(pattern), QueryRequest.generated_sql.ilike(pattern)))

    total = query.count()
    ordered = query.order_by(asc(QueryRequest.created_at) if order == "asc" else desc(QueryRequest.created_at))
    records = ordered.offset(skip).limit(effective_limit).all()
    return {
        "items": [_history_item(record) for record in records],
        "skip": skip,
        "limit": effective_limit,
        "total": total,
        "has_more": skip + len(records) < total,
    }


def get_query_lifecycle(db: Session, current_user_id: int, query_request_id: int) -> dict[str, Any]:
    query_request = db.query(QueryRequest).filter(QueryRequest.id == query_request_id, QueryRequest.user_id == current_user_id).first()
    if query_request is None:
        raise QueryHistoryRequestError("Query request not found", status.HTTP_404_NOT_FOUND)

    audit_query = db.query(AuditLog).filter(
        AuditLog.user_id == current_user_id,
        AuditLog.resource_type == "query_request",
        AuditLog.resource_id == str(query_request.id),
    )
    audit_count = audit_query.count()
    latest_event_at = audit_query.with_entities(func.max(AuditLog.created_at)).scalar()

    dataset = query_request.dataset
    maximum_bytes_billed = query_request.maximum_bytes_billed
    result_columns = query_request.result_columns or []
    return {
        "query": {
            "id": query_request.id,
            "user_id": query_request.user_id,
            "dataset_id": query_request.dataset_id,
            "dataset_name": _dataset_name(dataset),
            "bigquery_table_id": dataset.bigquery_table_id if dataset is not None else query_request.generated_for_table_id,
            "question": query_request.natural_language_question,
            "created_at": query_request.created_at,
            "updated_at": query_request.updated_at,
        },
        "generation": {
            "status": query_request.generation_status,
            "model_name": query_request.model_name,
            "generated_sql": query_request.generated_sql,
            "generated_for_table_id": query_request.generated_for_table_id,
            "error_message": query_request.error_message,
        },
        "validation": {
            "status": query_request.validation_status,
            "is_safe": query_request.is_safe,
            "statement_type": query_request.statement_type,
            "referenced_tables": query_request.referenced_tables or [],
            "errors": query_request.validation_errors or [],
            "warnings": query_request.validation_warnings or [],
            "validated_at": query_request.validated_at,
        },
        "dry_run": {
            "status": query_request.dry_run_status,
            "dry_run_valid": query_request.dry_run_valid,
            "estimated_bytes_processed": query_request.estimated_bytes_processed,
            "estimated_mib_processed": bytes_to_mib(query_request.estimated_bytes_processed),
            "estimated_gib_processed": bytes_to_gib(query_request.estimated_bytes_processed),
            "estimated_tib_processed": bytes_to_tib(query_request.estimated_bytes_processed),
            "maximum_bytes_billed": maximum_bytes_billed,
            "estimated_cost": _format_decimal(query_request.estimated_cost),
            "estimated_cost_currency": query_request.estimated_cost_currency,
            "bytes_limit_exceeded": query_request.bytes_limit_exceeded,
            "execution_eligible": query_request.execution_eligible,
            "dry_run_error": query_request.dry_run_error,
            "dry_run_job_id": query_request.dry_run_job_id,
            "dry_run_location": query_request.dry_run_location,
            "dry_run_at": query_request.dry_run_at,
        },
        "execution": {
            "status": query_request.execution_status,
            "execution_job_id": query_request.execution_job_id,
            "execution_location": query_request.execution_location,
            "execution_bytes_processed": query_request.execution_bytes_processed,
            "execution_bytes_billed": query_request.execution_bytes_billed,
            "execution_cache_hit": query_request.execution_cache_hit,
            "result_row_count": query_request.result_row_count,
            "result_columns": result_columns,
            "result_rows": query_request.result_rows or [],
            "result_truncated": query_request.result_truncated,
            "execution_error": query_request.execution_error,
            "execution_started_at": query_request.execution_started_at,
            "execution_completed_at": query_request.execution_completed_at,
            "executed_at": query_request.executed_at,
        },
        "audit_summary": {
            "total_events": audit_count,
            "latest_event_at": latest_event_at,
        },
    }

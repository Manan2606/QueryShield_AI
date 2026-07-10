from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.dataset import Dataset
from app.models.query_request import QueryRequest
from app.services.bigquery_service import run_query_dry_run

BYTES_PER_MIB = 1024**2
BYTES_PER_GIB = 1024**3
BYTES_PER_TIB = 1024**4
COST_QUANT = Decimal("0.000001")


class QueryDryRunRequestError(RuntimeError):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class QueryDryRunInternalError(RuntimeError):
    pass


def bytes_to_mib(bytes_value: int | None) -> float | None:
    return None if bytes_value is None else round(bytes_value / BYTES_PER_MIB, 6)


def bytes_to_gib(bytes_value: int | None) -> float | None:
    return None if bytes_value is None else round(bytes_value / BYTES_PER_GIB, 6)


def bytes_to_tib(bytes_value: int | None) -> float | None:
    return None if bytes_value is None else round(bytes_value / BYTES_PER_TIB, 9)


def calculate_estimated_cost(bytes_value: int | None) -> Decimal | None:
    if bytes_value is None:
        return None
    estimated_tib = Decimal(bytes_value) / Decimal(BYTES_PER_TIB)
    return (estimated_tib * settings.BIGQUERY_ON_DEMAND_PRICE_PER_TIB).quantize(COST_QUANT, rounding=ROUND_HALF_UP)


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


def _safe_error_message(exc: Exception, *, rejected: bool = False) -> str:
    class_name = exc.__class__.__name__
    text = str(exc).lower()
    if rejected:
        if "no such field" in text or "unrecognized name" in text or "unknown" in text:
            return "The query references a field that does not exist."
        if "not found" in text:
            return "The BigQuery table could not be found."
        return "BigQuery rejected the query during dry run."
    if class_name in {"DefaultCredentialsError", "RefreshError"} or "credential" in text:
        return "Google Cloud credentials are not configured correctly."
    if class_name in {"Forbidden", "PermissionDenied"} or "permission" in text:
        return "The configured identity does not have permission to run BigQuery jobs."
    if "api" in text and "disabled" in text:
        return "The BigQuery API may be disabled for the configured project."
    if "location" in text:
        return "BigQuery could not run the dry run because of a location mismatch."
    if "quota" in text:
        return "BigQuery could not run the dry run because a quota limit was reached."
    return "BigQuery dry run failed because of an application or Google Cloud configuration error."


def _is_bigquery_rejection(exc: Exception) -> bool:
    return exc.__class__.__name__ in {"BadRequest", "NotFound"}


def _execution_eligible(query_request: QueryRequest, maximum_bytes_billed: int) -> bool:
    return bool(
        query_request.generation_status == "generated"
        and query_request.validation_status == "passed"
        and query_request.is_safe is True
        and query_request.dry_run_status == "passed"
        and query_request.dry_run_valid is True
        and query_request.bytes_limit_exceeded is False
        and query_request.estimated_bytes_processed is not None
        and query_request.estimated_bytes_processed <= maximum_bytes_billed
    )


def _to_response(query_request: QueryRequest) -> dict[str, Any]:
    maximum_bytes_billed = query_request.maximum_bytes_billed or settings.MAX_BYTES_BILLED
    estimated_cost = query_request.estimated_cost
    return {
        "query_request_id": query_request.id,
        "dataset_id": query_request.dataset_id,
        "dry_run_status": query_request.dry_run_status,
        "dry_run_valid": bool(query_request.dry_run_valid),
        "estimated_bytes_processed": query_request.estimated_bytes_processed,
        "estimated_mib_processed": bytes_to_mib(query_request.estimated_bytes_processed),
        "estimated_gib_processed": bytes_to_gib(query_request.estimated_bytes_processed),
        "estimated_tib_processed": bytes_to_tib(query_request.estimated_bytes_processed),
        "maximum_bytes_billed": maximum_bytes_billed,
        "maximum_mib_billed": bytes_to_mib(maximum_bytes_billed) or 0,
        "bytes_limit_exceeded": bool(query_request.bytes_limit_exceeded),
        "estimated_cost": f"{estimated_cost:.6f}" if estimated_cost is not None else None,
        "estimated_cost_currency": query_request.estimated_cost_currency or settings.BIGQUERY_CURRENCY,
        "execution_eligible": bool(query_request.execution_eligible),
        "dry_run_error": query_request.dry_run_error,
        "dry_run_at": query_request.dry_run_at,
        "dry_run_job_id": query_request.dry_run_job_id,
        "dry_run_location": query_request.dry_run_location,
        "generated_sql": query_request.generated_sql or "",
        "warnings": [
            "Estimated cost is informational and may differ from actual billing because of pricing model, free usage, caching, discounts, reservations, and billing configuration."
        ] if estimated_cost is not None else [],
    }


def _load_owned_query(db: Session, current_user_id: int, query_request_id: int) -> QueryRequest:
    query_request = db.query(QueryRequest).filter(QueryRequest.id == query_request_id, QueryRequest.user_id == current_user_id).first()
    if query_request is None:
        raise QueryDryRunRequestError("Query request not found", status.HTTP_404_NOT_FOUND)
    return query_request


def _validate_dry_run_preconditions(db: Session, current_user_id: int, query_request: QueryRequest) -> Dataset:
    if query_request.generation_status != "generated":
        raise QueryDryRunRequestError("Query generation must succeed before dry run")
    if not query_request.generated_sql:
        raise QueryDryRunRequestError("Query request does not have generated SQL")
    if query_request.validation_status != "passed" or query_request.is_safe is not True:
        raise QueryDryRunRequestError("Query must pass SQL safety validation before dry run", status.HTTP_409_CONFLICT)

    dataset = db.query(Dataset).filter(Dataset.id == query_request.dataset_id, Dataset.owner_id == current_user_id).first()
    if dataset is None:
        raise QueryDryRunRequestError("Dataset not found", status.HTTP_404_NOT_FOUND)
    if dataset.status != "loaded":
        raise QueryDryRunRequestError("Dataset must be loaded into BigQuery before dry run")
    if not dataset.bigquery_table_id:
        raise QueryDryRunRequestError("Dataset does not have a BigQuery table ID")
    return dataset


def dry_run_query_request(db: Session, current_user_id: int, query_request_id: int) -> dict[str, Any]:
    query_request = _load_owned_query(db, current_user_id, query_request_id)
    dataset = _validate_dry_run_preconditions(db, current_user_id, query_request)
    maximum_bytes_billed = settings.MAX_BYTES_BILLED

    query_request.dry_run_status = "running"
    query_request.dry_run_valid = None
    query_request.estimated_bytes_processed = None
    query_request.maximum_bytes_billed = maximum_bytes_billed
    query_request.estimated_cost = None
    query_request.estimated_cost_currency = settings.BIGQUERY_CURRENCY
    query_request.bytes_limit_exceeded = None
    query_request.execution_eligible = False
    query_request.dry_run_error = None
    query_request.dry_run_job_id = None
    query_request.dry_run_location = None
    _add_audit_log(db, current_user_id, "query.dry_run_started", query_request.id, {"dataset_id": dataset.id})
    db.commit()
    db.refresh(query_request)

    try:
        result = run_query_dry_run(query_request.generated_sql or "")
        estimated_bytes = result.total_bytes_processed or 0
        bytes_limit_exceeded = estimated_bytes > maximum_bytes_billed
        query_request.dry_run_status = "blocked" if bytes_limit_exceeded else "passed"
        query_request.dry_run_valid = True
        query_request.estimated_bytes_processed = estimated_bytes
        query_request.maximum_bytes_billed = maximum_bytes_billed
        query_request.estimated_cost = calculate_estimated_cost(estimated_bytes)
        query_request.estimated_cost_currency = settings.BIGQUERY_CURRENCY
        query_request.bytes_limit_exceeded = bytes_limit_exceeded
        query_request.dry_run_error = None
        query_request.dry_run_at = datetime.utcnow()
        query_request.dry_run_job_id = result.job_id
        query_request.dry_run_location = result.location
        query_request.execution_eligible = _execution_eligible(query_request, maximum_bytes_billed)
        _add_audit_log(
            db,
            current_user_id,
            "query.dry_run_blocked" if bytes_limit_exceeded else "query.dry_run_passed",
            query_request.id,
            {
                "dataset_id": dataset.id,
                "estimated_bytes_processed": estimated_bytes,
                "maximum_bytes_billed": maximum_bytes_billed,
                "bytes_limit_exceeded": bytes_limit_exceeded,
                "execution_eligible": query_request.execution_eligible,
            },
        )
        db.commit()
        db.refresh(query_request)
        return _to_response(query_request)
    except Exception as exc:
        rejected = _is_bigquery_rejection(exc)
        query_request.dry_run_status = "failed" if rejected else "error"
        query_request.dry_run_valid = False
        query_request.estimated_bytes_processed = None
        query_request.maximum_bytes_billed = maximum_bytes_billed
        query_request.estimated_cost = None
        query_request.estimated_cost_currency = settings.BIGQUERY_CURRENCY
        query_request.bytes_limit_exceeded = False
        query_request.execution_eligible = False
        query_request.dry_run_error = _safe_error_message(exc, rejected=rejected)
        query_request.dry_run_at = datetime.utcnow()
        query_request.dry_run_job_id = None
        query_request.dry_run_location = None
        _add_audit_log(
            db,
            current_user_id,
            "query.dry_run_failed" if rejected else "query.dry_run_error",
            query_request.id,
            {"dataset_id": dataset.id, "error": query_request.dry_run_error},
        )
        db.commit()
        db.refresh(query_request)
        return _to_response(query_request)


def get_query_dry_run(db: Session, current_user_id: int, query_request_id: int) -> dict[str, Any]:
    query_request = _load_owned_query(db, current_user_id, query_request_id)
    if query_request.dry_run_status == "not_run":
        raise QueryDryRunRequestError("Query dry run has not been run")
    return _to_response(query_request)

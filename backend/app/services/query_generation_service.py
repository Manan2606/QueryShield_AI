from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.query_request import QueryRequest
from app.services.gemini_service import GeminiGenerationError, clean_generated_sql, generate_bigquery_sql, validate_generated_sql


class QueryGenerationError(RuntimeError):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _add_audit_log(
    db: Session,
    user_id: int,
    action: str,
    query_request_id: int | None = None,
    details: dict | None = None,
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
    message = str(exc).strip()
    return message or "SQL generation failed"


def _validation_summary(query_request: QueryRequest) -> dict:
    return {
        "validation_status": query_request.validation_status,
        "is_safe": query_request.is_safe,
        "validation_errors": query_request.validation_errors,
        "validation_warnings": query_request.validation_warnings,
        "validated_at": query_request.validated_at,
    }


def _to_generate_response(query_request: QueryRequest) -> dict:
    return {
        "id": query_request.id,
        "dataset_id": query_request.dataset_id,
        "question": query_request.natural_language_question,
        "generated_sql": query_request.generated_sql or "",
        "model_name": query_request.model_name,
        "status": query_request.generation_status,
        "created_at": query_request.created_at,
        **_validation_summary(query_request),
    }


def _to_summary(query_request: QueryRequest) -> dict:
    return {
        "id": query_request.id,
        "dataset_id": query_request.dataset_id,
        "question": query_request.natural_language_question,
        "generated_sql": query_request.generated_sql,
        "model_name": query_request.model_name,
        "status": query_request.generation_status,
        "error_message": query_request.error_message,
        "created_at": query_request.created_at,
        **_validation_summary(query_request),
    }


def generate_sql_for_dataset(db: Session, user_id: int, dataset_id: int, question: str) -> dict:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.owner_id == user_id).first()
    if dataset is None:
        raise QueryGenerationError("Dataset not found", status.HTTP_404_NOT_FOUND)

    query_request = QueryRequest(
        user_id=user_id,
        dataset_id=dataset_id,
        natural_language_question=question,
        generation_status="pending",
        model_name=settings.GEMINI_MODEL,
    )
    db.add(query_request)
    db.flush()
    _add_audit_log(db, user_id, "query.generation_started", query_request.id, {"dataset_id": dataset_id})
    db.commit()
    db.refresh(query_request)

    try:
        if dataset.status != "loaded":
            raise QueryGenerationError("Dataset must be loaded into BigQuery before SQL generation")
        if not dataset.bigquery_table_id:
            raise QueryGenerationError("Dataset does not have a BigQuery table ID")

        columns = (
            db.query(DatasetColumn)
            .filter(DatasetColumn.dataset_id == dataset.id)
            .order_by(DatasetColumn.ordinal_position)
            .all()
        )
        if not columns:
            raise QueryGenerationError("Dataset does not have stored schema columns")

        raw_sql = generate_bigquery_sql(dataset.bigquery_table_id, columns, question)
        cleaned_sql = clean_generated_sql(raw_sql)
        validated_sql = validate_generated_sql(cleaned_sql, dataset.bigquery_table_id).sql

        query_request.generated_sql = validated_sql
        query_request.model_name = settings.GEMINI_MODEL
        query_request.generation_status = "generated"
        query_request.error_message = None
        _add_audit_log(db, user_id, "query.generation_succeeded", query_request.id, {"dataset_id": dataset.id})
        db.commit()
        db.refresh(query_request)
        return _to_generate_response(query_request)
    except QueryGenerationError as exc:
        query_request.generation_status = "failed"
        query_request.error_message = _safe_error_message(exc)
        _add_audit_log(
            db,
            user_id,
            "query.generation_failed",
            query_request.id,
            {"dataset_id": dataset_id, "error": query_request.error_message},
        )
        db.commit()
        raise
    except GeminiGenerationError as exc:
        query_request.generation_status = "failed"
        query_request.error_message = _safe_error_message(exc)
        _add_audit_log(
            db,
            user_id,
            "query.generation_failed",
            query_request.id,
            {"dataset_id": dataset_id, "error": query_request.error_message},
        )
        db.commit()
        raise QueryGenerationError(query_request.error_message, status.HTTP_502_BAD_GATEWAY) from exc
    except Exception as exc:
        query_request.generation_status = "failed"
        query_request.error_message = _safe_error_message(exc)
        _add_audit_log(
            db,
            user_id,
            "query.generation_failed",
            query_request.id,
            {"dataset_id": dataset_id, "error": query_request.error_message},
        )
        db.commit()
        raise QueryGenerationError(query_request.error_message, status.HTTP_502_BAD_GATEWAY) from exc


def list_user_query_requests(db: Session, user_id: int, skip: int = 0, limit: int = 100, dataset_id: int | None = None) -> list[dict]:
    query = db.query(QueryRequest).filter(QueryRequest.user_id == user_id)
    if dataset_id is not None:
        query = query.filter(QueryRequest.dataset_id == dataset_id)
    records = query.order_by(QueryRequest.created_at.desc()).offset(skip).limit(limit).all()
    return [_to_summary(record) for record in records]


def get_user_query_request(db: Session, user_id: int, query_request_id: int) -> dict | None:
    record = db.query(QueryRequest).filter(QueryRequest.id == query_request_id, QueryRequest.user_id == user_id).first()
    if record is None:
        return None
    return _to_summary(record)

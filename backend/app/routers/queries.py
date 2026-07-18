from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.query_dry_run import QueryDryRunResponse
from app.schemas.query_execution import QueryExecuteRequest, QueryExecutionResponse
from app.schemas.audit import AuditLogListResponse
from app.schemas.query_generation import QueryGenerateRequest, QueryGenerateResponse
from app.schemas.query_history import QueryHistoryListResponse, QueryLifecycleResponse
from app.schemas.sql_validation import SQLValidationResponse
from app.services.query_dry_run_service import (
    QueryDryRunRequestError,
    dry_run_query_request,
    get_query_dry_run,
)
from app.services.query_execution_service import (
    QueryExecutionRequestError,
    execute_query_request,
    get_query_execution,
)
from app.services.audit_log_service import list_query_audit_logs
from app.services.query_generation_service import (
    QueryGenerationError,
    generate_sql_for_dataset,
)
from app.services.query_history_service import (
    QueryHistoryRequestError,
    get_query_lifecycle,
    list_query_history,
)
from app.services.sql_validation_service import (
    SQLValidationRequestError,
    SQLValidatorInternalError,
    get_query_validation,
    validate_query_request,
)


router = APIRouter(prefix="/queries", tags=["Queries"])


@router.post("/generate", response_model=QueryGenerateResponse)
def generate_query_sql(
    query_in: QueryGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryGenerateResponse:
    try:
        result = generate_sql_for_dataset(
            db, current_user.id, query_in.dataset_id, query_in.question
        )
    except QueryGenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return QueryGenerateResponse(**result)


@router.get("", response_model=QueryHistoryListResponse)
def list_queries(
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryHistoryListResponse:
    try:
        records = list_query_history(
            db,
            current_user.id,
            skip=skip,
            limit=limit,
            dataset_id=dataset_id,
            generation_status=generation_status,
            validation_status=validation_status,
            dry_run_status=dry_run_status,
            execution_status=execution_status,
            is_safe=is_safe,
            execution_eligible=execution_eligible,
            search=search,
            created_from=created_from,
            created_to=created_to,
            sort_order=sort_order,
        )
    except QueryHistoryRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return QueryHistoryListResponse(**records)


@router.post("/{query_request_id}/validate", response_model=SQLValidationResponse)
def validate_query_sql(
    query_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SQLValidationResponse:
    try:
        result = validate_query_request(db, current_user.id, query_request_id)
    except SQLValidationRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except SQLValidatorInternalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    return SQLValidationResponse(**result)


@router.get("/{query_request_id}/validation", response_model=SQLValidationResponse)
def read_query_validation(
    query_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SQLValidationResponse:
    try:
        result = get_query_validation(db, current_user.id, query_request_id)
    except SQLValidationRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return SQLValidationResponse(**result)


@router.post("/{query_request_id}/dry-run", response_model=QueryDryRunResponse)
def run_query_dry_run(
    query_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryDryRunResponse:
    try:
        result = dry_run_query_request(db, current_user.id, query_request_id)
    except QueryDryRunRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return QueryDryRunResponse(**result)


@router.get("/{query_request_id}/dry-run", response_model=QueryDryRunResponse)
def read_query_dry_run(
    query_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryDryRunResponse:
    try:
        result = get_query_dry_run(db, current_user.id, query_request_id)
    except QueryDryRunRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return QueryDryRunResponse(**result)


@router.post("/{query_request_id}/execute", response_model=QueryExecutionResponse)
def execute_stored_query(
    query_request_id: int,
    query_in: QueryExecuteRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryExecutionResponse:
    try:
        result = execute_query_request(
            db,
            current_user.id,
            query_request_id,
            requested_row_limit=query_in.row_limit if query_in is not None else None,
        )
    except QueryExecutionRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return QueryExecutionResponse(**result)


@router.get("/{query_request_id}/execution", response_model=QueryExecutionResponse)
def read_query_execution(
    query_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryExecutionResponse:
    try:
        result = get_query_execution(db, current_user.id, query_request_id)
    except QueryExecutionRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return QueryExecutionResponse(**result)


@router.get("/{query_request_id}/audit-logs", response_model=AuditLogListResponse)
def read_query_audit_logs(
    query_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditLogListResponse:
    try:
        result = list_query_audit_logs(db, current_user.id, query_request_id)
    except QueryHistoryRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return AuditLogListResponse(**result)


@router.get("/{query_request_id}", response_model=QueryLifecycleResponse)
def read_query(
    query_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryLifecycleResponse:
    try:
        record = get_query_lifecycle(db, current_user.id, query_request_id)
    except QueryHistoryRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return QueryLifecycleResponse(**record)

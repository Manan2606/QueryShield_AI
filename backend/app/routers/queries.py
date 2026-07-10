from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.query_dry_run import QueryDryRunResponse
from app.schemas.query_generation import QueryGenerateRequest, QueryGenerateResponse, QueryRequestSummary
from app.schemas.sql_validation import SQLValidationResponse
from app.services.query_dry_run_service import (
    QueryDryRunRequestError,
    dry_run_query_request,
    get_query_dry_run,
)
from app.services.query_generation_service import (
    QueryGenerationError,
    generate_sql_for_dataset,
    get_user_query_request,
    list_user_query_requests,
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
        result = generate_sql_for_dataset(db, current_user.id, query_in.dataset_id, query_in.question)
    except QueryGenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return QueryGenerateResponse(**result)


@router.get("", response_model=list[QueryRequestSummary])
def list_queries(
    skip: int = 0,
    limit: int = 100,
    dataset_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[QueryRequestSummary]:
    records = list_user_query_requests(db, current_user.id, skip=skip, limit=limit, dataset_id=dataset_id)
    return [QueryRequestSummary(**record) for record in records]


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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
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

@router.get("/{query_request_id}", response_model=QueryRequestSummary)
def read_query(
    query_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryRequestSummary:
    record = get_user_query_request(db, current_user.id, query_request_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query request not found")
    return QueryRequestSummary(**record)

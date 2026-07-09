from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.query_generation import QueryGenerateRequest, QueryGenerateResponse, QueryRequestSummary
from app.services.query_generation_service import (
    QueryGenerationError,
    generate_sql_for_dataset,
    get_user_query_request,
    list_user_query_requests,
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

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.audit import AuditLogListResponse
from app.services.audit_log_service import list_user_audit_logs
from app.services.query_history_service import QueryHistoryRequestError


router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    skip: int = 0,
    limit: int = 50,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditLogListResponse:
    try:
        result = list_user_audit_logs(
            db,
            current_user.id,
            skip=skip,
            limit=limit,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            created_from=created_from,
            created_to=created_to,
            sort_order=sort_order,
        )
    except QueryHistoryRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return AuditLogListResponse(**result)

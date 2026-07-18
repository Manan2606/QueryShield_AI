from datetime import datetime
from typing import Any

from fastapi import status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.query_request import QueryRequest
from app.services.query_history_service import (
    QueryHistoryRequestError,
    _validate_limit,
    _validate_sort_order,
)


def _audit_response(audit_log: AuditLog) -> dict[str, Any]:
    return {
        "id": audit_log.id,
        "action": audit_log.action,
        "resource_type": audit_log.resource_type,
        "resource_id": audit_log.resource_id,
        "details": audit_log.details,
        "created_at": audit_log.created_at,
    }


def list_user_audit_logs(
    db: Session,
    current_user_id: int,
    *,
    skip: int = 0,
    limit: int = 50,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort_order: str = "desc",
) -> dict[str, Any]:
    if skip < 0:
        raise QueryHistoryRequestError("skip must be greater than or equal to 0")
    effective_limit = _validate_limit(limit, 100)
    order = _validate_sort_order(sort_order)

    query = db.query(AuditLog).filter(AuditLog.user_id == current_user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.filter(AuditLog.resource_id == resource_id)
    if created_from is not None:
        query = query.filter(AuditLog.created_at >= created_from)
    if created_to is not None:
        query = query.filter(AuditLog.created_at <= created_to)

    total = query.count()
    ordered = query.order_by(
        asc(AuditLog.created_at) if order == "asc" else desc(AuditLog.created_at)
    )
    records = ordered.offset(skip).limit(effective_limit).all()
    return {
        "items": [_audit_response(record) for record in records],
        "skip": skip,
        "limit": effective_limit,
        "total": total,
        "has_more": skip + len(records) < total,
    }


def list_query_audit_logs(
    db: Session, current_user_id: int, query_request_id: int
) -> dict[str, Any]:
    query_request = (
        db.query(QueryRequest)
        .filter(
            QueryRequest.id == query_request_id, QueryRequest.user_id == current_user_id
        )
        .first()
    )
    if query_request is None:
        raise QueryHistoryRequestError(
            "Query request not found", status.HTTP_404_NOT_FOUND
        )

    records = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == current_user_id,
            AuditLog.resource_type == "query_request",
            AuditLog.resource_id == str(query_request.id),
        )
        .order_by(asc(AuditLog.created_at), asc(AuditLog.id))
        .all()
    )
    return {
        "items": [_audit_response(record) for record in records],
        "skip": 0,
        "limit": len(records),
        "total": len(records),
        "has_more": False,
    }

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

SENSITIVE_KEY_PARTS = (
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "credential",
    "credentials",
    "database_url",
    "jwt",
    "service_account",
)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def sanitize_audit_details(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                continue
            sanitized[key_text] = sanitize_audit_details(item)
        return sanitized
    if isinstance(value, (list, tuple, set)):
        return [sanitize_audit_details(item) for item in value]
    return str(value)


def create_audit_log(
    db: Session,
    user_id: int | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=sanitize_audit_details(details) if details is not None else None,
    )
    db.add(audit_log)
    return audit_log

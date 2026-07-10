from datetime import datetime

from pydantic import BaseModel


class SQLValidationResponse(BaseModel):
    query_request_id: int
    dataset_id: int
    validation_status: str
    is_safe: bool
    statement_type: str | None
    referenced_tables: list[str]
    errors: list[str]
    warnings: list[str]
    validated_at: datetime | None
    generated_sql: str
    normalized_sql: str | None = None

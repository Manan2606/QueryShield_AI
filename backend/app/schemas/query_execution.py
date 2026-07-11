from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QueryExecuteRequest(BaseModel):
    row_limit: int | None = Field(default=None, gt=0)

    model_config = ConfigDict(extra="forbid")


class QueryResultColumn(BaseModel):
    name: str
    field_type: str
    mode: str | None = None


class QueryExecutionResponse(BaseModel):
    query_request_id: int
    dataset_id: int
    execution_status: str
    execution_job_id: str | None
    execution_location: str | None
    execution_bytes_processed: int | None
    execution_bytes_billed: int | None
    execution_cache_hit: bool | None
    result_row_count: int
    result_columns: list[QueryResultColumn]
    result_rows: list[dict[str, Any]]
    result_truncated: bool
    row_limit: int
    execution_error: str | None
    execution_started_at: datetime | None
    execution_completed_at: datetime | None
    executed_at: datetime | None
    generated_sql: str


class QueryExecutionSummary(BaseModel):
    execution_status: str
    result_row_count: int | None
    result_truncated: bool | None
    execution_bytes_processed: int | None
    executed_at: datetime | None

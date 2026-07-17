from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.query_execution import QueryResultColumn


class QueryHistoryItem(BaseModel):
    id: int
    dataset_id: int
    dataset_name: str | None
    question: str
    generated_sql_preview: str | None
    generation_status: str
    validation_status: str
    is_safe: bool | None
    dry_run_status: str
    estimated_bytes_processed: int | None
    estimated_cost: str | None
    estimated_cost_currency: str | None
    bytes_limit_exceeded: bool | None
    execution_eligible: bool
    execution_status: str
    result_row_count: int | None
    result_truncated: bool | None
    created_at: datetime
    validated_at: datetime | None
    dry_run_at: datetime | None
    executed_at: datetime | None
    ai_summary: str | None
    ai_summary_status: str


class QueryHistoryListResponse(BaseModel):
    items: list[QueryHistoryItem]
    skip: int
    limit: int
    total: int
    has_more: bool


class QueryIdentitySection(BaseModel):
    id: int
    user_id: int
    dataset_id: int
    dataset_name: str | None
    bigquery_table_id: str | None
    question: str
    created_at: datetime
    updated_at: datetime


class QueryGenerationSection(BaseModel):
    status: str
    model_name: str | None
    generated_sql: str | None
    generated_for_table_id: str | None
    error_message: str | None


class QueryValidationSection(BaseModel):
    status: str
    is_safe: bool | None
    statement_type: str | None
    referenced_tables: list[str]
    errors: list[str]
    warnings: list[str]
    validated_at: datetime | None


class QueryDryRunSection(BaseModel):
    status: str
    dry_run_valid: bool | None
    estimated_bytes_processed: int | None
    estimated_mib_processed: float | None
    estimated_gib_processed: float | None
    estimated_tib_processed: float | None
    maximum_bytes_billed: int | None
    estimated_cost: str | None
    estimated_cost_currency: str | None
    bytes_limit_exceeded: bool | None
    execution_eligible: bool
    dry_run_error: str | None
    dry_run_job_id: str | None
    dry_run_location: str | None
    dry_run_at: datetime | None


class QueryExecutionSection(BaseModel):
    status: str
    execution_job_id: str | None
    execution_location: str | None
    execution_bytes_processed: int | None
    execution_bytes_billed: int | None
    execution_cache_hit: bool | None
    result_row_count: int | None
    result_columns: list[QueryResultColumn]
    result_rows: list[dict[str, Any]]
    result_truncated: bool | None
    execution_error: str | None
    execution_started_at: datetime | None
    execution_completed_at: datetime | None
    executed_at: datetime | None
    ai_summary: str | None
    ai_summary_status: str
    ai_summary_error: str | None
    ai_summary_generated_at: datetime | None


class QueryAuditSummary(BaseModel):
    total_events: int
    latest_event_at: datetime | None


class QueryLifecycleResponse(BaseModel):
    query: QueryIdentitySection
    generation: QueryGenerationSection
    validation: QueryValidationSection
    dry_run: QueryDryRunSection
    execution: QueryExecutionSection
    audit_summary: QueryAuditSummary

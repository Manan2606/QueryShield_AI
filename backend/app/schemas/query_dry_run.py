from datetime import datetime

from pydantic import BaseModel


class QueryDryRunResponse(BaseModel):
    query_request_id: int
    dataset_id: int
    dry_run_status: str
    dry_run_valid: bool
    estimated_bytes_processed: int | None
    estimated_mib_processed: float | None
    estimated_gib_processed: float | None
    estimated_tib_processed: float | None
    maximum_bytes_billed: int
    maximum_mib_billed: float
    bytes_limit_exceeded: bool
    estimated_cost: str | None
    estimated_cost_currency: str
    execution_eligible: bool
    dry_run_error: str | None
    dry_run_at: datetime | None
    dry_run_job_id: str | None
    dry_run_location: str | None
    generated_sql: str
    warnings: list[str] = []

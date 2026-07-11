"""add query execution fields

Revision ID: 20260710_0007
Revises: 20260710_0006
Create Date: 2026-07-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260710_0007"
down_revision: str | None = "20260710_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("query_requests", sa.Column("generated_for_table_id", sa.String(), nullable=True))
    op.execute(
        """
        UPDATE query_requests
        SET generated_for_table_id = (
            SELECT datasets.bigquery_table_id
            FROM datasets
            WHERE datasets.id = query_requests.dataset_id
        )
        WHERE generation_status = 'generated'
          AND generated_for_table_id IS NULL
        """
    )
    op.add_column("query_requests", sa.Column("execution_status", sa.String(), nullable=False, server_default="not_executed"))
    op.add_column("query_requests", sa.Column("execution_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("query_requests", sa.Column("execution_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("query_requests", sa.Column("execution_error", sa.Text(), nullable=True))
    op.add_column("query_requests", sa.Column("execution_job_id", sa.String(), nullable=True))
    op.add_column("query_requests", sa.Column("execution_location", sa.String(), nullable=True))
    op.add_column("query_requests", sa.Column("execution_bytes_processed", sa.BigInteger(), nullable=True))
    op.add_column("query_requests", sa.Column("execution_bytes_billed", sa.BigInteger(), nullable=True))
    op.add_column("query_requests", sa.Column("execution_cache_hit", sa.Boolean(), nullable=True))
    op.add_column("query_requests", sa.Column("result_row_count", sa.Integer(), nullable=True))
    op.add_column("query_requests", sa.Column("result_columns", sa.JSON(), nullable=True))
    op.add_column("query_requests", sa.Column("result_rows", sa.JSON(), nullable=True))
    op.add_column("query_requests", sa.Column("result_truncated", sa.Boolean(), nullable=True))
    op.add_column("query_requests", sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("query_requests", "executed_at")
    op.drop_column("query_requests", "result_truncated")
    op.drop_column("query_requests", "result_rows")
    op.drop_column("query_requests", "result_columns")
    op.drop_column("query_requests", "result_row_count")
    op.drop_column("query_requests", "execution_cache_hit")
    op.drop_column("query_requests", "execution_bytes_billed")
    op.drop_column("query_requests", "execution_bytes_processed")
    op.drop_column("query_requests", "execution_location")
    op.drop_column("query_requests", "execution_job_id")
    op.drop_column("query_requests", "execution_error")
    op.drop_column("query_requests", "execution_completed_at")
    op.drop_column("query_requests", "execution_started_at")
    op.drop_column("query_requests", "execution_status")
    op.drop_column("query_requests", "generated_for_table_id")

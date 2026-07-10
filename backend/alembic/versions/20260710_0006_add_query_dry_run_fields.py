"""add query dry run fields

Revision ID: 20260710_0006
Revises: 20260709_0005
Create Date: 2026-07-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260710_0006"
down_revision: str | None = "20260709_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("query_requests", sa.Column("dry_run_status", sa.String(), nullable=False, server_default="not_run"))
    op.add_column("query_requests", sa.Column("dry_run_valid", sa.Boolean(), nullable=True))
    op.add_column("query_requests", sa.Column("estimated_bytes_processed", sa.BigInteger(), nullable=True))
    op.add_column("query_requests", sa.Column("maximum_bytes_billed", sa.BigInteger(), nullable=True))
    op.add_column("query_requests", sa.Column("estimated_cost", sa.Numeric(18, 6), nullable=True))
    op.add_column("query_requests", sa.Column("estimated_cost_currency", sa.String(), nullable=True))
    op.add_column("query_requests", sa.Column("bytes_limit_exceeded", sa.Boolean(), nullable=True))
    op.add_column("query_requests", sa.Column("execution_eligible", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("query_requests", sa.Column("dry_run_error", sa.Text(), nullable=True))
    op.add_column("query_requests", sa.Column("dry_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("query_requests", sa.Column("dry_run_job_id", sa.String(), nullable=True))
    op.add_column("query_requests", sa.Column("dry_run_location", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("query_requests", "dry_run_location")
    op.drop_column("query_requests", "dry_run_job_id")
    op.drop_column("query_requests", "dry_run_at")
    op.drop_column("query_requests", "dry_run_error")
    op.drop_column("query_requests", "execution_eligible")
    op.drop_column("query_requests", "bytes_limit_exceeded")
    op.drop_column("query_requests", "estimated_cost_currency")
    op.drop_column("query_requests", "estimated_cost")
    op.drop_column("query_requests", "maximum_bytes_billed")
    op.drop_column("query_requests", "estimated_bytes_processed")
    op.drop_column("query_requests", "dry_run_valid")
    op.drop_column("query_requests", "dry_run_status")

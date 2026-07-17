"""add ai result summary fields

Revision ID: 20260716_0009
Revises: 20260710_0008
Create Date: 2026-07-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260716_0009"
down_revision: str | None = "20260710_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("query_requests", sa.Column("ai_summary", sa.Text(), nullable=True))
    op.add_column("query_requests", sa.Column("ai_summary_status", sa.String(), nullable=False, server_default="not_available"))
    op.add_column("query_requests", sa.Column("ai_summary_error", sa.Text(), nullable=True))
    op.add_column("query_requests", sa.Column("ai_summary_generated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("query_requests", "ai_summary_generated_at")
    op.drop_column("query_requests", "ai_summary_error")
    op.drop_column("query_requests", "ai_summary_status")
    op.drop_column("query_requests", "ai_summary")

"""add query validation fields

Revision ID: 20260709_0005
Revises: 20260708_0004
Create Date: 2026-07-09 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260709_0005"
down_revision: str | None = "20260708_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "query_requests",
        sa.Column("validation_status", sa.String(), nullable=False, server_default="not_validated"),
    )
    op.add_column("query_requests", sa.Column("is_safe", sa.Boolean(), nullable=True))
    op.add_column("query_requests", sa.Column("statement_type", sa.String(), nullable=True))
    op.add_column("query_requests", sa.Column("validation_errors", sa.JSON(), nullable=True))
    op.add_column("query_requests", sa.Column("validation_warnings", sa.JSON(), nullable=True))
    op.add_column("query_requests", sa.Column("referenced_tables", sa.JSON(), nullable=True))
    op.add_column("query_requests", sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("query_requests", "validated_at")
    op.drop_column("query_requests", "referenced_tables")
    op.drop_column("query_requests", "validation_warnings")
    op.drop_column("query_requests", "validation_errors")
    op.drop_column("query_requests", "statement_type")
    op.drop_column("query_requests", "is_safe")
    op.drop_column("query_requests", "validation_status")

"""add history and audit indexes

Revision ID: 20260710_0008
Revises: 20260710_0007
Create Date: 2026-07-10 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260710_0008"
down_revision: str | None = "20260710_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_query_requests_user_created_at", "query_requests", ["user_id", "created_at"])
    op.create_index("ix_query_requests_user_dataset", "query_requests", ["user_id", "dataset_id"])
    op.create_index("ix_query_requests_user_execution_status", "query_requests", ["user_id", "execution_status"])
    op.create_index("ix_audit_logs_user_created_at", "audit_logs", ["user_id", "created_at"])
    op.create_index("ix_audit_logs_user_resource", "audit_logs", ["user_id", "resource_type", "resource_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_user_resource", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_created_at", table_name="audit_logs")
    op.drop_index("ix_query_requests_user_execution_status", table_name="query_requests")
    op.drop_index("ix_query_requests_user_dataset", table_name="query_requests")
    op.drop_index("ix_query_requests_user_created_at", table_name="query_requests")

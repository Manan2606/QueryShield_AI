"""create query requests table

Revision ID: 20260708_0004
Revises: 20260706_0003
Create Date: 2026-07-08 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260708_0004"
down_revision: str | None = "20260706_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "query_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("natural_language_question", sa.Text(), nullable=False),
        sa.Column("generated_sql", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("generation_status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_query_requests_dataset_id"), "query_requests", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_query_requests_id"), "query_requests", ["id"], unique=False)
    op.create_index(op.f("ix_query_requests_user_id"), "query_requests", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_query_requests_user_id"), table_name="query_requests")
    op.drop_index(op.f("ix_query_requests_id"), table_name="query_requests")
    op.drop_index(op.f("ix_query_requests_dataset_id"), table_name="query_requests")
    op.drop_table("query_requests")

"""add dataset load status fields

Revision ID: 20260706_0003
Revises: 20260704_0002
Create Date: 2026-07-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260706_0003"
down_revision: str | None = "20260704_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("datasets", sa.Column("load_error", sa.Text(), nullable=True))
    op.add_column("datasets", sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("datasets", "loaded_at")
    op.drop_column("datasets", "load_error")

"""add network status table

Revision ID: c5e8a1d4f729
Revises: 0d3f6a8b2c41
Create Date: 2026-10-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c5e8a1d4f729"
down_revision: str | None = "0d3f6a8b2c41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "network_status",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("simid", sa.Integer(), nullable=False),
        sa.Column("imsi", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=255), nullable=False),
        sa.Column("start", sa.DateTime(), nullable=False),
        sa.Column("profiletype", sa.String(length=255), nullable=False),
        sa.Column("statusmodification", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_network_status_id"), "network_status", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_network_status_id"), table_name="network_status")
    op.drop_table("network_status")

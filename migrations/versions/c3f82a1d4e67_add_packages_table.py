"""add packages table

Revision ID: c3f82a1d4e67
Revises: 82a0d3e9f6b1
Create Date: 2026-09-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3f82a1d4e67"
down_revision: str | None = "82a0d3e9f6b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "packages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("sparkid", sa.Integer(), nullable=True),
        sa.Column("reward", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_packages_id"), "packages", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_packages_id"), table_name="packages")
    op.drop_table("packages")

"""add currencies table

Revision ID: e4d1c9b2a806
Revises: b8a3d6e9f120
Create Date: 2026-09-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e4d1c9b2a806"
down_revision: str | None = "b8a3d6e9f120"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "currencies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("symbol_native", sa.String(length=10), nullable=False),
        sa.Column("decimal_digits", sa.Integer(), nullable=False),
        sa.Column("rounding", sa.Integer(), nullable=False),
        sa.Column("iso_numeric", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iso_numeric"),
    )
    op.create_index(op.f("ix_currencies_code"), "currencies", ["code"], unique=True)
    op.create_index(op.f("ix_currencies_id"), "currencies", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_currencies_id"), table_name="currencies")
    op.drop_index(op.f("ix_currencies_code"), table_name="currencies")
    op.drop_table("currencies")

"""add email whitelist table

Revision ID: e6b29f13a4c8
Revises: d4e8a2c1f907
Create Date: 2026-09-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6b29f13a4c8"
down_revision: str | None = "d4e8a2c1f907"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_whitelist",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("createdate", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="UNIQ_EMAILWHITELIST_EMAIL"),
    )


def downgrade() -> None:
    op.drop_table("email_whitelist")

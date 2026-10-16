"""add eSIM status and network columns

Revision ID: 8d4f2a6c9b31
Revises: c9e6f4a2b718
Create Date: 2026-10-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8d4f2a6c9b31"
down_revision: str | None = "c9e6f4a2b718"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("esims", sa.Column("mobileplanid", sa.Integer(), nullable=True))
    op.add_column("esims", sa.Column("activationdate", sa.DateTime(), nullable=True))
    op.add_column("esims", sa.Column("lastusagedate", sa.DateTime(), nullable=True))
    op.add_column("esims", sa.Column("subscriber_status", sa.String(length=255), nullable=True))
    op.add_column("esims", sa.Column("lastnetworkdate", sa.DateTime(), nullable=True))
    op.add_column("esims", sa.Column("lastmcc", sa.String(length=255), nullable=True))
    op.add_column("esims", sa.Column("lastmnc", sa.String(length=255), nullable=True))
    op.add_column("esims", sa.Column("lastcellid", sa.Integer(), nullable=True))
    op.add_column("esims", sa.Column("lastlac", sa.Integer(), nullable=True))
    op.add_column("esims", sa.Column("lastrat", sa.String(length=255), nullable=True))


def downgrade() -> None:
    for column in (
        "lastrat",
        "lastlac",
        "lastcellid",
        "lastmnc",
        "lastmcc",
        "lastnetworkdate",
        "subscriber_status",
        "lastusagedate",
        "activationdate",
        "mobileplanid",
    ):
        op.drop_column("esims", column)

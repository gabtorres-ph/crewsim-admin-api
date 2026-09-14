"""add sms table

Revision ID: 9b1d7e5c3a42
Revises: f2c8b7d91a34
Create Date: 2026-09-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9b1d7e5c3a42"
down_revision: str | None = "f2c8b7d91a34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("userid", sa.Integer(), nullable=False),
        sa.Column("imsi", sa.String(length=100), nullable=False),
        sa.Column("sender", sa.String(length=100), nullable=False),
        sa.Column("smstext", sa.String(length=3000), nullable=False),
        sa.Column("template", sa.String(length=100), nullable=True),
        sa.Column("language", sa.String(length=2), nullable=False),
        sa.Column("createdate", sa.DateTime(), nullable=False),
        sa.Column("sentdate", sa.DateTime(), nullable=True),
        sa.Column("sentresultcode", sa.String(length=50), nullable=True),
        sa.Column("sentresulttext", sa.String(length=150), nullable=True),
        sa.Column("retrycounter", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("userid_idx", "sms", ["userid"], unique=False)
    op.create_index("imsi_idx", "sms", ["imsi"], unique=False)
    op.create_index("createdate_idx", "sms", ["createdate"], unique=False)
    op.create_index("sentresultcode_idx", "sms", ["sentresultcode"], unique=False)
    op.create_index("sentdate_idx", "sms", ["sentdate"], unique=False)


def downgrade() -> None:
    op.drop_index("sentdate_idx", table_name="sms")
    op.drop_index("sentresultcode_idx", table_name="sms")
    op.drop_index("createdate_idx", table_name="sms")
    op.drop_index("imsi_idx", table_name="sms")
    op.drop_index("userid_idx", table_name="sms")
    op.drop_table("sms")

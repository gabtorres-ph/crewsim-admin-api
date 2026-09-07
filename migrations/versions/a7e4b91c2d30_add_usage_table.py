"""add usage table

Revision ID: a7e4b91c2d30
Revises: c3f82a1d4e67
Create Date: 2026-09-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7e4b91c2d30"
down_revision: str | None = "c3f82a1d4e67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usage_date_utc", sa.DateTime(), nullable=False),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column("mcc", sa.Integer(), nullable=False),
        sa.Column("mnc", sa.Integer(), nullable=False),
        sa.Column("total_qty", sa.Integer(), nullable=False),
        sa.Column("usage_type_id", sa.Integer(), nullable=False),
        sa.Column("usage_type", sa.String(length=100), nullable=False),
        sa.Column("dest_phone_number", sa.String(length=100), nullable=True),
        sa.Column("subs_reseller_name", sa.String(length=100), nullable=False),
        sa.Column("custo_account_name", sa.String(length=100), nullable=False),
        sa.Column("subs_account_name", sa.String(length=100), nullable=False),
        sa.Column("subscriber_id", sa.Integer(), nullable=False),
        sa.Column("imsi", sa.String(length=100), nullable=False),
        sa.Column("iccid", sa.String(length=100), nullable=False),
        sa.Column("subs_phone_number", sa.String(length=100), nullable=False),
        sa.Column("prepaid_package_ids", sa.String(length=100), nullable=False),
        sa.Column("prepaid_package_qtys", sa.String(length=100), nullable=False),
        sa.Column("toll_free", sa.String(length=10), nullable=False),
        sa.Column("CUSTO_ACCOUNT_ID", sa.Integer(), nullable=True),
        sa.Column("custo_charge", sa.Numeric(precision=20, scale=15), nullable=True),
        sa.Column("subs_account_id", sa.Integer(), nullable=True),
        sa.Column("subs_charge", sa.Numeric(precision=20, scale=15), nullable=True),
        sa.Column("apn", sa.String(length=100), nullable=False),
        sa.Column("rat", sa.Integer(), nullable=False),
        sa.Column("imei", sa.String(length=100), nullable=False),
        sa.Column("down_bitrate", sa.BigInteger(), nullable=False),
        sa.Column("up_bitrate", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_usage_date_utc", "usage", ["usage_date_utc"], unique=False)
    op.create_index("idx_imsi", "usage", ["imsi"], unique=False)
    op.create_index("idx_iccid", "usage", ["iccid"], unique=False)
    op.create_index("idx_imsi_usage_dt", "usage", ["imsi", "usage_date_utc"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_imsi_usage_dt", table_name="usage")
    op.drop_index("idx_iccid", table_name="usage")
    op.drop_index("idx_imsi", table_name="usage")
    op.drop_index("idx_usage_date_utc", table_name="usage")
    op.drop_table("usage")

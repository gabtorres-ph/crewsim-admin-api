"""add stripe notification table

Revision ID: f2c8b7d91a34
Revises: e6b29f13a4c8
Create Date: 2026-09-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2c8b7d91a34"
down_revision: str | None = "e6b29f13a4c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stripenotification",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("eventid", sa.String(length=100), nullable=False),
        sa.Column("invoiceid", sa.String(length=100), nullable=False),
        sa.Column("customerid", sa.String(length=100), nullable=False),
        sa.Column("taxrate", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("taxcountry", sa.String(length=100), nullable=True),
        sa.Column("amount_net", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("amount_tax", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("amount_gross", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=100), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("userid", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("createdate", sa.DateTime(), nullable=False),
        sa.Column("imsi", sa.String(length=100), nullable=True),
        sa.Column("amount_credit", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_stripenotification_eventid", "stripenotification", ["eventid"], unique=False
    )
    op.create_index(
        "idx_stripenotification_invoiceid", "stripenotification", ["invoiceid"], unique=False
    )
    op.create_index(
        "idx_stripenotification_customerid", "stripenotification", ["customerid"], unique=False
    )
    op.create_index(
        "idx_stripenotification_userid", "stripenotification", ["userid"], unique=False
    )
    op.create_index(
        "idx_stripenotification_createdate", "stripenotification", ["createdate"], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_stripenotification_createdate", table_name="stripenotification")
    op.drop_index("idx_stripenotification_userid", table_name="stripenotification")
    op.drop_index("idx_stripenotification_customerid", table_name="stripenotification")
    op.drop_index("idx_stripenotification_invoiceid", table_name="stripenotification")
    op.drop_index("idx_stripenotification_eventid", table_name="stripenotification")
    op.drop_table("stripenotification")

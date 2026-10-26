"""add roaming plan details table

Revision ID: 2c6f8a1d9e43
Revises: d7f3a1c9e624
Create Date: 2026-10-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "2c6f8a1d9e43"
down_revision: str | None = "d7f3a1c9e624"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roaming_plan_details",
        sa.Column("roaming_plan_rule_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("roaming_plan_id", sa.Integer(), nullable=False),
        sa.Column("network_id", sa.Integer(), nullable=False),
        sa.Column("continent", sa.String(length=100), nullable=False),
        sa.Column("country_name", sa.String(length=100), nullable=False),
        sa.Column("country_iso2", sa.String(length=2), nullable=False),
        sa.Column("operator_name", sa.String(length=255), nullable=False),
        sa.Column(
            "mcc_mncs",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "tadigs",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("data_rate", sa.Numeric(precision=20, scale=10), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["roaming_plan_id"],
            ["roaming_plans.id"],
            name="fk_roaming_plan_details_roaming_plan_id_roaming_plans",
        ),
        sa.PrimaryKeyConstraint("roaming_plan_rule_id"),
    )


def downgrade() -> None:
    op.drop_table("roaming_plan_details")

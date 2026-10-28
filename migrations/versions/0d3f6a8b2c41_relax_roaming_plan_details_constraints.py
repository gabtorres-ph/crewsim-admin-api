"""relax roaming plan details constraints

Revision ID: 0d3f6a8b2c41
Revises: 9c4e1b7a2d68
Create Date: 2026-10-29 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0d3f6a8b2c41"
down_revision: str | None = "9c4e1b7a2d68"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "fk_roaming_plan_details_roaming_plan_id_roaming_plans",
        "roaming_plan_details",
        type_="foreignkey",
    )
    op.alter_column(
        "roaming_plan_details",
        "data_rate",
        existing_type=sa.Numeric(precision=20, scale=10),
        nullable=True,
    )


def downgrade() -> None:
    connection = op.get_bind()
    missing_data_rates = connection.execute(
        sa.text("SELECT COUNT(*) FROM roaming_plan_details WHERE data_rate IS NULL")
    ).scalar_one()
    if missing_data_rates:
        raise RuntimeError(
            f"Cannot downgrade: {missing_data_rates} roaming plan detail(s) have no data rate. "
            "Set each data rate before downgrading."
        )

    missing_roaming_plans = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM roaming_plan_details AS detail "
            "LEFT JOIN roaming_plans AS plan ON plan.id = detail.roaming_plan_id "
            "WHERE plan.id IS NULL"
        )
    ).scalar_one()
    if missing_roaming_plans:
        raise RuntimeError(
            f"Cannot downgrade: {missing_roaming_plans} roaming plan detail(s) reference missing "
            "roaming plans. Create each roaming plan or reassign its details before downgrading."
        )

    op.alter_column(
        "roaming_plan_details",
        "data_rate",
        existing_type=sa.Numeric(precision=20, scale=10),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_roaming_plan_details_roaming_plan_id_roaming_plans",
        "roaming_plan_details",
        "roaming_plans",
        ["roaming_plan_id"],
        ["id"],
    )

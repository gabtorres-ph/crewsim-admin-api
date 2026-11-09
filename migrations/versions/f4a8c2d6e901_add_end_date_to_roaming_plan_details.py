"""add end date to roaming plan details

Revision ID: f4a8c2d6e901
Revises: c5e8a1d4f729
Create Date: 2026-11-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f4a8c2d6e901"
down_revision: str | None = "c5e8a1d4f729"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "roaming_plan_details",
        sa.Column("end_date", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("roaming_plan_details", "end_date")

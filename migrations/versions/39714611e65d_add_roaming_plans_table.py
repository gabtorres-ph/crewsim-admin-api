"""add roaming plans table

Revision ID: 39714611e65d
Revises: a2f7c9d4e681
Create Date: 2026-10-23 09:08:40.823942

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "39714611e65d"
down_revision: str | None = "a2f7c9d4e681"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roaming_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("roaming_plan_name", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("roaming_plans")

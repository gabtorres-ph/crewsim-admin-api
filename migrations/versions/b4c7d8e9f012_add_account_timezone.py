"""add account timezone

Revision ID: b4c7d8e9f012
Revises: f6a1c8d3e742
Create Date: 2026-10-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b4c7d8e9f012"
down_revision: str | None = "f6a1c8d3e742"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "time_zone",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
    )
    op.create_index(op.f("ix_time_zone_id"), "time_zone", ["id"], unique=False)
    op.create_unique_constraint("uq_time_zone_name", "time_zone", ["name"])
    op.drop_constraint("time_zone_pkey", "time_zone", type_="primary")
    op.create_primary_key("pk_time_zone", "time_zone", ["id"])

    op.add_column("accounts", sa.Column("timezone", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_accounts_timezone_time_zone",
        "accounts",
        "time_zone",
        ["timezone"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_accounts_timezone_time_zone", "accounts", type_="foreignkey")
    op.drop_column("accounts", "timezone")

    op.drop_constraint("pk_time_zone", "time_zone", type_="primary")
    op.create_primary_key("time_zone_pkey", "time_zone", ["name"])
    op.drop_constraint("uq_time_zone_name", "time_zone", type_="unique")
    op.drop_index(op.f("ix_time_zone_id"), table_name="time_zone")
    op.drop_column("time_zone", "id")

"""refresh accounts from telcovision

Revision ID: 3b8d5f2a7c91
Revises: 5e7b2c9d1f48
Create Date: 2026-10-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3b8d5f2a7c91"
down_revision: str | None = "5e7b2c9d1f48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("reseller_id", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("package_only", sa.Boolean(), nullable=True))
    op.add_column("accounts", sa.Column("steering_list_id", sa.Integer(), nullable=True))
    op.alter_column("esims", "accountid", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    unlinked = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM esims WHERE accountid IS NULL")
    ).scalar_one()
    if unlinked:
        raise RuntimeError(
            f"Cannot downgrade: {unlinked} eSIM(s) have no account. "
            "Assign each eSIM to an account before downgrading."
        )
    op.alter_column("esims", "accountid", existing_type=sa.Integer(), nullable=False)
    op.drop_column("accounts", "steering_list_id")
    op.drop_column("accounts", "package_only")
    op.drop_column("accounts", "reseller_id")

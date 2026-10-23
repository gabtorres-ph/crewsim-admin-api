"""add account currency

Revision ID: f6a1c8d3e742
Revises: 39714611e65d
Create Date: 2026-10-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f6a1c8d3e742"
down_revision: str | None = "39714611e65d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("currency", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_accounts_currency_currencies",
        "accounts",
        "currencies",
        ["currency"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_accounts_currency_currencies", "accounts", type_="foreignkey")
    op.drop_column("accounts", "currency")

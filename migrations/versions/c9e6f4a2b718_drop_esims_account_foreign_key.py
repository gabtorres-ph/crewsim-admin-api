"""drop the foreign key between esims and accounts

Revision ID: c9e6f4a2b718
Revises: 3b8d5f2a7c91
Create Date: 2026-10-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c9e6f4a2b718"
down_revision: str | None = "3b8d5f2a7c91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("fk_esims_accountid_accounts", "esims", type_="foreignkey")


def downgrade() -> None:
    orphaned = op.get_bind().execute(
        sa.text(
            "SELECT COUNT(*) FROM esims AS e "
            "LEFT JOIN accounts AS a ON a.id = e.accountid "
            "WHERE e.accountid IS NOT NULL AND a.id IS NULL"
        )
    ).scalar_one()
    if orphaned:
        raise RuntimeError(
            f"Cannot downgrade: {orphaned} eSIM(s) reference missing accounts. "
            "Assign each eSIM to an existing account or clear its account ID before downgrading."
        )
    op.create_foreign_key("fk_esims_accountid_accounts", "esims", "accounts", ["accountid"], ["id"])

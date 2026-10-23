"""add account language

Revision ID: d7f3a1c9e624
Revises: b4c7d8e9f012
Create Date: 2026-10-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d7f3a1c9e624"
down_revision: str | None = "b4c7d8e9f012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("language", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_accounts_language_languages",
        "accounts",
        "languages",
        ["language"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_accounts_language_languages", "accounts", type_="foreignkey")
    op.drop_column("accounts", "language")

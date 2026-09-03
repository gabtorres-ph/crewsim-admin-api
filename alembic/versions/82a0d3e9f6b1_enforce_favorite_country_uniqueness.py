"""enforce favorite country uniqueness per user

Revision ID: 82a0d3e9f6b1
Revises: 4f9a6c1e2b7d
Create Date: 2026-08-31 18:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "82a0d3e9f6b1"
down_revision: str | None = "4f9a6c1e2b7d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_favorites_userid_country", "favorites", ["userid", "country"])


def downgrade() -> None:
    op.drop_constraint("uq_favorites_userid_country", "favorites", type_="unique")

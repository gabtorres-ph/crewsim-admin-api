"""enforce user email uniqueness

Revision ID: ce3d0bca6997
Revises: 20260809_users_esims
Create Date: 2026-08-13 12:55:30.332259

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ce3d0bca6997"
down_revision: str | None = "20260809_users_esims"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")

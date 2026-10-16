"""enforce eSIM IMSI uniqueness

Revision ID: a2f7c9d4e681
Revises: 8d4f2a6c9b31
Create Date: 2026-10-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a2f7c9d4e681"
down_revision: str | None = "8d4f2a6c9b31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    duplicate_imsis = op.get_bind().execute(
        sa.text(
            "SELECT COUNT(*) FROM ("
            "SELECT imsi FROM esims GROUP BY imsi HAVING COUNT(*) > 1"
            ") AS duplicate_imsis"
        )
    ).scalar_one()
    if duplicate_imsis:
        raise RuntimeError(
            f"Cannot enforce eSIM IMSI uniqueness: {duplicate_imsis} IMSI value(s) "
            "are shared by multiple eSIM records. "
            "Find them with SELECT imsi, COUNT(*) FROM esims GROUP BY imsi "
            "HAVING COUNT(*) > 1; resolve the duplicate records explicitly, "
            "then rerun the migration. No records were deleted or merged."
        )
    op.create_unique_constraint("uq_esims_imsi", "esims", ["imsi"])


def downgrade() -> None:
    op.drop_constraint("uq_esims_imsi", "esims", type_="unique")

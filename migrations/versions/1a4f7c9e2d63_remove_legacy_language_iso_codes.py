"""remove legacy language ISO codes

Revision ID: 1a4f7c9e2d63
Revises: 6d2e8f4a9c10
Create Date: 2026-09-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1a4f7c9e2d63"
down_revision: str | None = "6d2e8f4a9c10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_languages_iso2b", "languages", type_="unique")
    op.drop_constraint("uq_languages_iso2t", "languages", type_="unique")
    op.drop_constraint("uq_languages_iso3", "languages", type_="unique")
    op.drop_index(op.f("ix_languages_iso3"), table_name="languages")
    op.drop_column("languages", "iso2b")
    op.drop_column("languages", "iso2t")
    op.drop_column("languages", "iso3")


def downgrade() -> None:
    op.add_column("languages", sa.Column("iso3", sa.String(length=3), nullable=True))
    op.add_column("languages", sa.Column("iso2t", sa.String(length=3), nullable=True))
    op.add_column("languages", sa.Column("iso2b", sa.String(length=3), nullable=True))
    op.create_index(op.f("ix_languages_iso3"), "languages", ["iso3"], unique=False)
    op.create_unique_constraint("uq_languages_iso3", "languages", ["iso3"])
    op.create_unique_constraint("uq_languages_iso2t", "languages", ["iso2t"])
    op.create_unique_constraint("uq_languages_iso2b", "languages", ["iso2b"])

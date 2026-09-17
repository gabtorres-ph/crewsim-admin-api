"""add languages table

Revision ID: 7c1e5a9b3d24
Revises: e4d1c9b2a806
Create Date: 2026-09-17 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7c1e5a9b3d24"
down_revision: str | None = "e4d1c9b2a806"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "languages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("iso1", sa.String(length=2), nullable=True),
        sa.Column("iso2b", sa.String(length=3), nullable=True),
        sa.Column("iso2t", sa.String(length=3), nullable=True),
        sa.Column("iso3", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iso1", name="uq_languages_iso1"),
        sa.UniqueConstraint("iso2b", name="uq_languages_iso2b"),
        sa.UniqueConstraint("iso2t", name="uq_languages_iso2t"),
        sa.UniqueConstraint("iso3", name="uq_languages_iso3"),
    )
    op.create_index(op.f("ix_languages_id"), "languages", ["id"], unique=False)
    op.create_index(op.f("ix_languages_iso1"), "languages", ["iso1"], unique=False)
    op.create_index(op.f("ix_languages_iso3"), "languages", ["iso3"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_languages_iso3"), table_name="languages")
    op.drop_index(op.f("ix_languages_iso1"), table_name="languages")
    op.drop_index(op.f("ix_languages_id"), table_name="languages")
    op.drop_table("languages")

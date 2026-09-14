"""add countries table

Revision ID: b8a3d6e9f120
Revises: 9b1d7e5c3a42
Create Date: 2026-09-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b8a3d6e9f120"
down_revision: str | None = "9b1d7e5c3a42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cc2", sa.String(length=2), nullable=False),
        sa.Column("cc3", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("continent", sa.String(length=2), nullable=True),
        sa.Column("flag_emoji", sa.String(length=16), nullable=True),
        sa.Column("flag_url1", sa.String(length=255), nullable=True),
        sa.Column("flag_url2", sa.String(length=255), nullable=True),
        sa.Column("country_square", sa.String(length=255), nullable=True),
        sa.Column("country_rectangle", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cc2", name="uq_countries_cc2"),
        sa.UniqueConstraint("cc3", name="uq_countries_cc3"),
    )
    op.create_index(op.f("ix_countries_cc2"), "countries", ["cc2"], unique=False)
    op.create_index(op.f("ix_countries_cc3"), "countries", ["cc3"], unique=False)
    op.create_index(op.f("ix_countries_id"), "countries", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_countries_id"), table_name="countries")
    op.drop_index(op.f("ix_countries_cc3"), table_name="countries")
    op.drop_index(op.f("ix_countries_cc2"), table_name="countries")
    op.drop_table("countries")

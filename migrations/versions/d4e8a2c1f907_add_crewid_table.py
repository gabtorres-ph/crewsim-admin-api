"""add crewid table

Revision ID: d4e8a2c1f907
Revises: a7e4b91c2d30
Create Date: 2026-09-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e8a2c1f907"
down_revision: str | None = "a7e4b91c2d30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crewid",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("unique_id", sa.String(length=50), nullable=False),
        sa.Column("file1", sa.String(length=100), nullable=True),
        sa.Column("file2", sa.String(length=100), nullable=True),
        sa.Column("firstname", sa.String(length=150), nullable=True),
        sa.Column("lastname", sa.String(length=150), nullable=True),
        sa.Column("airline", sa.String(length=150), nullable=True),
        sa.Column("iscrewid", sa.Boolean(), nullable=False),
        sa.Column("createdate", sa.DateTime(), nullable=False),
        sa.Column("userid", sa.Integer(), nullable=True),
        sa.Column("file1_hash", sa.String(length=64), nullable=True),
        sa.Column("file2_hash", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("type", sa.String(length=255), nullable=True),
        sa.Column("dhash", sa.String(length=32), nullable=True),
        sa.Column("phash", sa.String(length=32), nullable=True),
        sa.Column("dhash_distance", sa.Integer(), nullable=True),
        sa.Column("phash_distance", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("IDX_file1_hash", "crewid", ["file1_hash"], unique=False)
    op.create_index("IDX_file2_hash", "crewid", ["file2_hash"], unique=False)
    op.create_index("IDX_unique_id", "crewid", ["unique_id"], unique=False)
    op.create_index("IDX_userid", "crewid", ["userid"], unique=False)
    op.create_index("idx_crewid_dhash", "crewid", ["dhash"], unique=False)
    op.create_index("idx_crewid_phash", "crewid", ["phash"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_crewid_phash", table_name="crewid")
    op.drop_index("idx_crewid_dhash", table_name="crewid")
    op.drop_index("IDX_userid", table_name="crewid")
    op.drop_index("IDX_unique_id", table_name="crewid")
    op.drop_index("IDX_file2_hash", table_name="crewid")
    op.drop_index("IDX_file1_hash", table_name="crewid")
    op.drop_table("crewid")

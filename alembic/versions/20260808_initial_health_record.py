"""initial health record table

Revision ID: 20260808_initial_health_record
Revises: 
Create Date: 2026-08-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260808_initial_health_record"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "health_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_health_records_id"), "health_records", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_health_records_id"), table_name="health_records")
    op.drop_table("health_records")

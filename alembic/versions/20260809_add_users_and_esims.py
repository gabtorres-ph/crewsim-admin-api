"""add users and esims tables

Revision ID: 20260809_users_esims
Revises: 20260808_initial_health_record
Create Date: 2026-08-09 00:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260809_users_esims"
down_revision = "20260808_initial_health_record"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("language", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "esims",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("userid", sa.Integer(), nullable=False),
        sa.Column("imsi", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["userid"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_esims_id"), "esims", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_esims_id"), table_name="esims")
    op.drop_table("esims")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

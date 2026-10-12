"""add sim notification table

Revision ID: 5e7b2c9d1f48
Revises: 1a4f7c9e2d63
Create Date: 2026-10-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "5e7b2c9d1f48"
down_revision: str | None = "1a4f7c9e2d63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sim_notification",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("typ", sa.String(length=20), nullable=False),
        sa.Column("imsi", sa.String(length=15), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("createdate", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sim_notification_typ", "sim_notification", ["typ"], unique=False)
    op.create_index("idx_sim_notification_imsi", "sim_notification", ["imsi"], unique=False)
    op.create_index(
        "idx_sim_notification_createdate", "sim_notification", ["createdate"], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_sim_notification_createdate", table_name="sim_notification")
    op.drop_index("idx_sim_notification_imsi", table_name="sim_notification")
    op.drop_index("idx_sim_notification_typ", table_name="sim_notification")
    op.drop_table("sim_notification")

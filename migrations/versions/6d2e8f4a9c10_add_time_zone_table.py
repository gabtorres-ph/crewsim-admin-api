"""add time_zone table and seed IANA timezone identifiers

Revision ID: 6d2e8f4a9c10
Revises: 7c1e5a9b3d24
Create Date: 2026-09-18 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6d2e8f4a9c10"
down_revision: str | None = "7c1e5a9b3d24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "time_zone",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("name"),
    )
    # Use the server's IANA database, including compatibility aliases and UTC.
    # Exclude host-local entries and duplicate POSIX/leap-second directory trees.
    op.execute(
        sa.text(
            """
            INSERT INTO time_zone (name)
            SELECT name
            FROM pg_timezone_names
            WHERE name NOT LIKE 'posix/%'
              AND name NOT LIKE 'right/%'
              AND name NOT IN ('localtime', 'posixrules')
            ORDER BY name
            """
        )
    )


def downgrade() -> None:
    op.drop_table("time_zone")

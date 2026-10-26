"""merge roaming plan details and locale heads

Revision ID: bc2d68b42359
Revises: 2c6f8a1d9e43, a9c2e7f4b613
Create Date: 2026-10-26 14:56:01.589969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc2d68b42359'
down_revision: Union[str, None] = ('2c6f8a1d9e43', 'a9c2e7f4b613')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

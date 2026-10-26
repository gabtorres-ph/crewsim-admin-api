"""seed languages

Revision ID: 9c4e1b7a2d68
Revises: 7f3c2a9e6d14
Create Date: 2026-10-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from alembic import op

revision: str = "9c4e1b7a2d68"
down_revision: str | None = "7f3c2a9e6d14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LANGUAGES = [
    {"iso1": "bg", "name": "Bulgarian"},
    {"iso1": "cs", "name": "Czech"},
    {"iso1": "da", "name": "Danish"},
    {"iso1": "de", "name": "German"},
    {"iso1": "en", "name": "English"},
    {"iso1": "es", "name": "Spanish"},
    {"iso1": "fr", "name": "French"},
    {"iso1": "he", "name": "Hebrew"},
    {"iso1": "hi", "name": "Hindi"},
    {"iso1": "hu", "name": "Hungarian"},
    {"iso1": "id", "name": "Indonesian"},
    {"iso1": "is", "name": "Icelandic"},
    {"iso1": "ja", "name": "Japanese"},
    {"iso1": "ko", "name": "Korean"},
    {"iso1": "ms", "name": "Malay"},
    {"iso1": "nb", "name": "Norwegian Bokmål"},
    {"iso1": "pl", "name": "Polish"},
    {"iso1": "pt", "name": "Portuguese"},
    {"iso1": "ro", "name": "Romanian"},
    {"iso1": "sv", "name": "Swedish"},
    {"iso1": "th", "name": "Thai"},
    {"iso1": "tl", "name": "Tagalog"},
    {"iso1": "tr", "name": "Turkish"},
    {"iso1": "zh", "name": "Chinese"},
]


def upgrade() -> None:
    languages = sa.table(
        "languages",
        sa.column("iso1", sa.String(length=2)),
        sa.column("name", sa.String(length=150)),
    )
    statement = insert(languages).values(LANGUAGES)
    op.get_bind().execute(
        statement.on_conflict_do_update(
            index_elements=[languages.c.iso1],
            set_={"name": statement.excluded.name},
        )
    )


def downgrade() -> None:
    # Seeded rows may predate this migration or be referenced by application data.
    pass

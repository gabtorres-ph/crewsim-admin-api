"""replace user locale IDs with values

Revision ID: e1a7c4d9b205
Revises: bc2d68b42359
Create Date: 2026-10-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e1a7c4d9b205"
down_revision: str | None = "bc2d68b42359"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("lang_iso1", sa.String(length=2), nullable=True))
    op.add_column("users", sa.Column("currency_code", sa.String(length=3), nullable=True))
    op.add_column("users", sa.Column("timezone_name", sa.Text(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE users
            SET lang_iso1 = languages.iso1
            FROM languages
            WHERE users.language = languages.id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET currency_code = currencies.code
            FROM currencies
            WHERE users.currency = currencies.id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET timezone_name = time_zone.name
            FROM time_zone
            WHERE users.timezone = time_zone.id
            """
        )
    )

    unmapped = op.get_bind().execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM users
            WHERE lang_iso1 IS NULL
               OR currency_code IS NULL
               OR timezone_name IS NULL
            """
        )
    ).scalar_one()
    if unmapped:
        raise RuntimeError(
            f"Cannot replace user locale IDs: {unmapped} user(s) have locale IDs "
            "that cannot be mapped to a language ISO1 code, currency code, and timezone name."
        )

    op.drop_constraint("fk_users_language_languages", "users", type_="foreignkey")
    op.drop_constraint("fk_users_currency_currencies", "users", type_="foreignkey")
    op.drop_constraint("fk_users_timezone_time_zone", "users", type_="foreignkey")
    op.drop_column("users", "language")
    op.drop_column("users", "currency")
    op.drop_column("users", "timezone")
    op.alter_column(
        "users",
        "timezone_name",
        new_column_name="timezone",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.alter_column(
        "users",
        "lang_iso1",
        existing_type=sa.String(length=2),
        nullable=False,
    )
    op.alter_column(
        "users",
        "currency_code",
        existing_type=sa.String(length=3),
        nullable=False,
    )


def downgrade() -> None:
    op.add_column("users", sa.Column("language_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("currency_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("timezone_id", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE users
            SET language_id = languages.id
            FROM languages
            WHERE users.lang_iso1 = languages.iso1
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET currency_id = currencies.id
            FROM currencies
            WHERE users.currency_code = currencies.code
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET timezone_id = time_zone.id
            FROM time_zone
            WHERE users.timezone = time_zone.name
            """
        )
    )

    unmapped = op.get_bind().execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM users
            WHERE language_id IS NULL
               OR currency_id IS NULL
               OR timezone_id IS NULL
            """
        )
    ).scalar_one()
    if unmapped:
        raise RuntimeError(
            f"Cannot downgrade: {unmapped} user(s) have locale values that do not match "
            "a language, currency, and timezone lookup row."
        )

    op.drop_column("users", "lang_iso1")
    op.drop_column("users", "currency_code")
    op.drop_column("users", "timezone")
    op.alter_column(
        "users",
        "language_id",
        new_column_name="language",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "users",
        "currency_id",
        new_column_name="currency",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "users",
        "timezone_id",
        new_column_name="timezone",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_users_language_languages",
        "users",
        "languages",
        ["language"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_users_currency_currencies",
        "users",
        "currencies",
        ["currency"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_users_timezone_time_zone",
        "users",
        "time_zone",
        ["timezone"],
        ["id"],
    )

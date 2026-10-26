"""move locale fields to users

Revision ID: a9c2e7f4b613
Revises: d7f3a1c9e624
Create Date: 2026-10-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a9c2e7f4b613"
down_revision: str | None = "d7f3a1c9e624"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("language_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("currency_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("timezone_id", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE users AS users_to_update
            SET language_id = languages.id
            FROM languages
            WHERE lower(trim(users_to_update.language)) = lower(languages.iso1)
               OR lower(trim(users_to_update.language)) = lower(languages.name)
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users AS users_to_update
            SET currency_id = currencies.id
            FROM currencies
            WHERE lower(trim(users_to_update.currency)) = lower(currencies.code)
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users AS users_to_update
            SET timezone_id = time_zone.id
            FROM time_zone
            WHERE lower(trim(users_to_update.timezone)) = lower(time_zone.name)
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM users
                    WHERE language_id IS NULL
                       OR currency_id IS NULL
                       OR timezone_id IS NULL
                ) THEN
                    RAISE EXCEPTION
                        'Cannot map every user language, currency, and timezone to lookup IDs';
                END IF;
            END
            $$
            """
        )
    )

    op.drop_column("users", "language")
    op.drop_column("users", "currency")
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

    op.drop_constraint("fk_accounts_currency_currencies", "accounts", type_="foreignkey")
    op.drop_constraint("fk_accounts_language_languages", "accounts", type_="foreignkey")
    op.drop_constraint("fk_accounts_timezone_time_zone", "accounts", type_="foreignkey")
    op.drop_column("accounts", "currency")
    op.drop_column("accounts", "language")
    op.drop_column("accounts", "timezone")


def downgrade() -> None:
    op.add_column("accounts", sa.Column("currency", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("language", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("timezone", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_accounts_currency_currencies",
        "accounts",
        "currencies",
        ["currency"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_accounts_language_languages",
        "accounts",
        "languages",
        ["language"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_accounts_timezone_time_zone",
        "accounts",
        "time_zone",
        ["timezone"],
        ["id"],
    )

    op.add_column("users", sa.Column("language_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("currency_code", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("timezone_name", sa.String(length=255), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE users
            SET language_name = coalesce(languages.iso1, languages.name)
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

    op.drop_constraint("fk_users_language_languages", "users", type_="foreignkey")
    op.drop_constraint("fk_users_currency_currencies", "users", type_="foreignkey")
    op.drop_constraint("fk_users_timezone_time_zone", "users", type_="foreignkey")
    op.drop_column("users", "language")
    op.drop_column("users", "currency")
    op.drop_column("users", "timezone")
    op.alter_column(
        "users",
        "language_name",
        new_column_name="language",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        "users",
        "currency_code",
        new_column_name="currency",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        "users",
        "timezone_name",
        new_column_name="timezone",
        existing_type=sa.String(length=255),
        nullable=False,
    )

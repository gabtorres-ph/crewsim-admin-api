"""add account, profile, and eSIM detail columns

Revision ID: 4f9a6c1e2b7d
Revises: ce3d0bca6997
Create Date: 2026-08-31 17:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "4f9a6c1e2b7d"
down_revision: str | None = "ce3d0bca6997"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_accounts_id"), "accounts", ["id"], unique=False)

    op.add_column("users", sa.Column("firstname", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("lastname", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("airline", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("position", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("referralcode", sa.String(length=8), nullable=True))
    op.add_column("users", sa.Column("referredby", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("stripeid", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("logtoid", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("createdate", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("newsletter", sa.Boolean(), nullable=True))
    op.add_column("users", sa.Column("smsnotification", sa.Boolean(), nullable=True))
    op.add_column("users", sa.Column("rateus", sa.DateTime(), nullable=True))
    op.create_foreign_key("fk_users_referredby_users", "users", "users", ["referredby"], ["id"])

    op.add_column("esims", sa.Column("accountid", sa.Integer(), nullable=True))
    op.add_column("esims", sa.Column("name", sa.String(length=255), nullable=True))
    op.add_column("esims", sa.Column("isesim", sa.Boolean(), nullable=True))
    op.add_column("esims", sa.Column("createdate", sa.DateTime(), nullable=True))
    op.add_column("esims", sa.Column("token", sa.String(length=8), nullable=True))
    op.add_column("esims", sa.Column("networkstatus", sa.String(length=255), nullable=True))
    op.add_column("esims", sa.Column("balance", sa.Float(), nullable=True))
    op.add_column(
        "esims",
        sa.Column("use_account_for_charging", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("esims", sa.Column("smdpserver", sa.String(length=255), nullable=True))
    op.add_column("esims", sa.Column("activationcode", sa.String(length=255), nullable=True))
    op.add_column("esims", sa.Column("imei", sa.String(length=255), nullable=True))
    op.add_column("esims", sa.Column("imei_device", sa.String(length=255), nullable=True))
    op.add_column("esims", sa.Column("allow_data", sa.Boolean(), nullable=True))

    # Preserve existing eSIM records by assigning them to one explicitly marked account.
    op.execute(
        sa.text(
            "INSERT INTO accounts (name, balance) "
            "SELECT 'Migrated account', 0 "
            "WHERE EXISTS (SELECT 1 FROM esims)"
        )
    )
    op.execute(
        sa.text(
            "UPDATE esims SET accountid = (SELECT MIN(id) FROM accounts) "
            "WHERE accountid IS NULL"
        )
    )
    op.alter_column("esims", "accountid", existing_type=sa.Integer(), nullable=False)
    op.alter_column("esims", "userid", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key("fk_esims_accountid_accounts", "esims", "accounts", ["accountid"], ["id"])
    op.alter_column("esims", "use_account_for_charging", server_default=None)

    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("userid", sa.Integer(), nullable=False),
        sa.Column("country", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["userid"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_favorites_id"), "favorites", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_favorites_id"), table_name="favorites")
    op.drop_table("favorites")

    op.drop_constraint("fk_esims_accountid_accounts", "esims", type_="foreignkey")
    op.alter_column("esims", "userid", existing_type=sa.Integer(), nullable=False)
    for column in (
        "allow_data", "imei_device", "imei", "activationcode", "smdpserver",
        "use_account_for_charging", "balance", "networkstatus", "token", "createdate",
        "isesim", "name", "accountid",
    ):
        op.drop_column("esims", column)

    op.drop_constraint("fk_users_referredby_users", "users", type_="foreignkey")
    for column in (
        "rateus", "smsnotification", "newsletter", "createdate", "logtoid", "stripeid",
        "referredby", "referralcode", "position", "airline", "lastname", "firstname",
    ):
        op.drop_column("users", column)

    op.drop_index(op.f("ix_accounts_id"), table_name="accounts")
    op.drop_table("accounts")

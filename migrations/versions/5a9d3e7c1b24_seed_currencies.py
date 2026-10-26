"""seed currencies

Revision ID: 5a9d3e7c1b24
Revises: e1a7c4d9b205
Create Date: 2026-10-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from alembic import op

revision: str = "5a9d3e7c1b24"
down_revision: str | None = "e1a7c4d9b205"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CURRENCIES = [
    {
        "code": "AUD",
        "name": "Australian Dollar",
        "symbol": "$",
        "symbol_native": "$",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 36,
    },
    {
        "code": "BGN",
        "name": "Bulgarian Lev",
        "symbol": "лв",
        "symbol_native": "лв",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 975,
    },
    {
        "code": "BRL",
        "name": "Brazilian Real",
        "symbol": "R$",
        "symbol_native": "R$",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 986,
    },
    {
        "code": "CAD",
        "name": "Canadian Dollar",
        "symbol": "$",
        "symbol_native": "$",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 124,
    },
    {
        "code": "CHF",
        "name": "Swiss Franc",
        "symbol": "CHF",
        "symbol_native": "CHF",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 756,
    },
    {
        "code": "CNY",
        "name": "Chinese Yuan",
        "symbol": "¥",
        "symbol_native": "¥",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 156,
    },
    {
        "code": "CZK",
        "name": "Czech Koruna",
        "symbol": "Kč",
        "symbol_native": "Kč",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 203,
    },
    {
        "code": "DKK",
        "name": "Danish Krone",
        "symbol": "kr",
        "symbol_native": "kr",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 208,
    },
    {
        "code": "GBP",
        "name": "British Pound Sterling",
        "symbol": "£",
        "symbol_native": "£",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 826,
    },
    {
        "code": "HKD",
        "name": "Hong Kong Dollar",
        "symbol": "$",
        "symbol_native": "$",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 344,
    },
    {
        "code": "HUF",
        "name": "Hungarian Forint",
        "symbol": "Ft",
        "symbol_native": "Ft",
        "decimal_digits": 0,
        "rounding": 0,
        "iso_numeric": 348,
    },
    {
        "code": "IDR",
        "name": "Indonesian Rupiah",
        "symbol": "Rp",
        "symbol_native": "Rp",
        "decimal_digits": 0,
        "rounding": 0,
        "iso_numeric": 360,
    },
    {
        "code": "ILS",
        "name": "Israeli New Shekel",
        "symbol": "₪",
        "symbol_native": "₪",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 376,
    },
    {
        "code": "INR",
        "name": "Indian Rupee",
        "symbol": "₹",
        "symbol_native": "₹",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 356,
    },
    {
        "code": "ISK",
        "name": "Icelandic Króna",
        "symbol": "kr",
        "symbol_native": "kr",
        "decimal_digits": 0,
        "rounding": 0,
        "iso_numeric": 352,
    },
    {
        "code": "JPY",
        "name": "Japanese Yen",
        "symbol": "¥",
        "symbol_native": "¥",
        "decimal_digits": 0,
        "rounding": 0,
        "iso_numeric": 392,
    },
    {
        "code": "KRW",
        "name": "South Korean Won",
        "symbol": "₩",
        "symbol_native": "₩",
        "decimal_digits": 0,
        "rounding": 0,
        "iso_numeric": 410,
    },
    {
        "code": "MXN",
        "name": "Mexican Peso",
        "symbol": "$",
        "symbol_native": "$",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 484,
    },
    {
        "code": "MYR",
        "name": "Malaysian Ringgit",
        "symbol": "RM",
        "symbol_native": "RM",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 458,
    },
    {
        "code": "NOK",
        "name": "Norwegian Krone",
        "symbol": "kr",
        "symbol_native": "kr",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 578,
    },
    {
        "code": "NZD",
        "name": "New Zealand Dollar",
        "symbol": "$",
        "symbol_native": "$",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 554,
    },
    {
        "code": "PHP",
        "name": "Philippine Peso",
        "symbol": "₱",
        "symbol_native": "₱",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 608,
    },
    {
        "code": "PLN",
        "name": "Polish Złoty",
        "symbol": "zł",
        "symbol_native": "zł",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 985,
    },
    {
        "code": "RON",
        "name": "Romanian Leu",
        "symbol": "lei",
        "symbol_native": "lei",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 946,
    },
    {
        "code": "SEK",
        "name": "Swedish Krona",
        "symbol": "kr",
        "symbol_native": "kr",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 752,
    },
    {
        "code": "SGD",
        "name": "Singapore Dollar",
        "symbol": "$",
        "symbol_native": "$",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 702,
    },
    {
        "code": "THB",
        "name": "Thai Baht",
        "symbol": "฿",
        "symbol_native": "฿",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 764,
    },
    {
        "code": "TRY",
        "name": "Turkish Lira",
        "symbol": "₺",
        "symbol_native": "₺",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 949,
    },
    {
        "code": "USD",
        "name": "US Dollar",
        "symbol": "$",
        "symbol_native": "$",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 840,
    },
    {
        "code": "ZAR",
        "name": "South African Rand",
        "symbol": "R",
        "symbol_native": "R",
        "decimal_digits": 2,
        "rounding": 0,
        "iso_numeric": 710,
    },
]


def upgrade() -> None:
    currencies = sa.table(
        "currencies",
        sa.column("code", sa.String(length=3)),
        sa.column("name", sa.String(length=100)),
        sa.column("symbol", sa.String(length=10)),
        sa.column("symbol_native", sa.String(length=10)),
        sa.column("decimal_digits", sa.Integer()),
        sa.column("rounding", sa.Integer()),
        sa.column("iso_numeric", sa.Integer()),
    )
    statement = insert(currencies).values(CURRENCIES)
    op.get_bind().execute(
        statement.on_conflict_do_update(
            index_elements=[currencies.c.code],
            set_={
                "name": statement.excluded.name,
                "symbol": statement.excluded.symbol,
                "symbol_native": statement.excluded.symbol_native,
                "decimal_digits": statement.excluded.decimal_digits,
                "rounding": statement.excluded.rounding,
                "iso_numeric": statement.excluded.iso_numeric,
            },
        )
    )


def downgrade() -> None:
    # Seeded rows may predate this migration or be referenced by application data.
    pass

"""Create deterministic development data for manual end-to-end testing."""

from argparse import ArgumentParser
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ESIM, Account, User


@dataclass(frozen=True)
class SeedRecord:
    email: str
    language: str
    currency: str
    timezone: str
    imsi: str


@dataclass(frozen=True)
class SeedResult:
    created_users: int
    existing_users: int
    created_esims: int
    existing_esims: int


SEED_RECORDS = (
    SeedRecord(
        email="alex.morgan@example.test",
        language="en",
        currency="USD",
        timezone="America/New_York",
        imsi="001010000000001",
    ),
    SeedRecord(
        email="sofia.rossi@example.test",
        language="it",
        currency="EUR",
        timezone="Europe/Rome",
        imsi="001010000000002",
    ),
    SeedRecord(
        email="haruto.sato@example.test",
        language="ja",
        currency="JPY",
        timezone="Asia/Tokyo",
        imsi="001010000000003",
    ),
    SeedRecord(
        email="maria.santos@example.test",
        language="fil",
        currency="PHP",
        timezone="Asia/Manila",
        imsi="001010000000004",
    ),
    SeedRecord(
        email="lucas.silva@example.test",
        language="pt",
        currency="BRL",
        timezone="America/Sao_Paulo",
        imsi="001010000000005",
    ),
    SeedRecord(
        email="amelie.dubois@example.test",
        language="fr",
        currency="EUR",
        timezone="Europe/Paris",
        imsi="001010000000006",
    ),
    SeedRecord(
        email="kwame.mensah@example.test",
        language="en",
        currency="GHS",
        timezone="Africa/Accra",
        imsi="001010000000007",
    ),
    SeedRecord(
        email="emma.wilson@example.test",
        language="en",
        currency="AUD",
        timezone="Australia/Sydney",
        imsi="001010000000008",
    ),
    SeedRecord(
        email="noah.mueller@example.test",
        language="de",
        currency="EUR",
        timezone="Europe/Berlin",
        imsi="001010000000009",
    ),
    SeedRecord(
        email="priya.sharma@example.test",
        language="hi",
        currency="INR",
        timezone="Asia/Kolkata",
        imsi="001010000000010",
    ),
)


def seed_database(session: Session, records: Sequence[SeedRecord]) -> SeedResult:
    """Insert missing seed records in one transaction and leave existing data unchanged."""
    emails = [record.email for record in records]
    imsis = [record.imsi for record in records]

    created_users = 0
    created_esims = 0

    with session.begin():
        account = session.scalar(select(Account).where(Account.name == "Seed account"))
        if account is None:
            account = Account(name="Seed account", balance=0)
            session.add(account)
            session.flush()

        users_by_email = {
            user.email: user for user in session.scalars(select(User).where(User.email.in_(emails)))
        }
        esims_by_imsi = {
            esim.imsi: esim for esim in session.scalars(select(ESIM).where(ESIM.imsi.in_(imsis)))
        }

        for record in records:
            user = users_by_email.get(record.email)
            if user is None:
                user = User(
                    email=record.email,
                    language=record.language,
                    currency=record.currency,
                    timezone=record.timezone,
                )
                session.add(user)
                session.flush()
                users_by_email[record.email] = user
                created_users += 1

            esim = esims_by_imsi.get(record.imsi)
            if esim is None:
                esim = ESIM(userid=user.id, accountid=account.id, imsi=record.imsi)
                session.add(esim)
                esims_by_imsi[record.imsi] = esim
                created_esims += 1
            elif esim.userid != user.id:
                raise RuntimeError(
                    f"Seed IMSI {record.imsi} already belongs to user {esim.userid}, "
                    f"not {user.id} ({record.email})"
                )

    return SeedResult(
        created_users=created_users,
        existing_users=len(records) - created_users,
        created_esims=created_esims,
        existing_esims=len(records) - created_esims,
    )


def parse_args() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--count",
        type=int,
        choices=range(5, 11),
        default=8,
        help="number of user/eSIM pairs to seed (default: 8)",
    )
    return parser


def main() -> None:
    args = parse_args().parse_args()
    with SessionLocal() as session:
        result = seed_database(session, SEED_RECORDS[: args.count])

    print(
        "Seed complete: "
        f"users {result.created_users} created/{result.existing_users} existing; "
        f"eSIMs {result.created_esims} created/{result.existing_esims} existing."
    )


if __name__ == "__main__":
    main()

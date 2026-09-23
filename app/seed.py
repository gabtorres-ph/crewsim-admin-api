"""Create deterministic development data for manual end-to-end testing."""

from argparse import ArgumentParser
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import Account
from app.database import SessionLocal
from app.esims.models import ESIM
from app.favorites.models import Favorite  # noqa: F401 -- registers User relationship target
from app.usage.models import Usage
from app.users.models import User


@dataclass(frozen=True)
class SeedRecord:
    email: str
    language: str
    currency: str
    timezone: str
    imsi: str
    firstname: str | None = None
    lastname: str | None = None
    airline: str | None = None
    position: str | None = None
    referralcode: str | None = None
    stripeid: str | None = None
    logtoid: str | None = None
    createdate: datetime | None = None
    newsletter: bool | None = None
    smsnotification: bool | None = None
    rateus: datetime | None = None
    esim_name: str | None = None
    isesim: bool | None = None
    esim_createdate: datetime | None = None
    token: str | None = None
    networkstatus: str | None = None
    balance: float | None = None
    use_account_for_charging: bool = False
    smdpserver: str | None = None
    activationcode: str | None = None
    imei: str | None = None
    imei_device: str | None = None
    allow_data: bool | None = None


@dataclass(frozen=True)
class SeedResult:
    created_users: int
    existing_users: int
    created_esims: int
    existing_esims: int
    created_usage: int
    existing_usage: int


@dataclass(frozen=True)
class UsageSeedRecord:
    usage_date_utc: datetime
    session_id: str
    mcc: int
    mnc: int
    total_qty: int
    usage_type_id: int
    usage_type: str
    dest_phone_number: str | None
    subs_reseller_name: str
    custo_account_name: str
    subs_account_name: str
    subscriber_id: int
    imsi: str
    iccid: str
    subs_phone_number: str
    prepaid_package_ids: str
    prepaid_package_qtys: str
    toll_free: str
    custo_account_id: int | None
    custo_charge: Decimal | None
    subs_account_id: int | None
    subs_charge: Decimal | None
    apn: str
    rat: int
    imei: str
    down_bitrate: int
    up_bitrate: int
    filename: str


SEED_PROFILES = (
    ("Alex", "Morgan", "en", "USD", "America/New_York", "Delta Air Lines", "Captain"),
    ("Sofia", "Rossi", "it", "EUR", "Europe/Rome", "ITA Airways", "First Officer"),
    ("Haruto", "Sato", "ja", "JPY", "Asia/Tokyo", "Japan Airlines", "Purser"),
    ("Maria", "Santos", "fil", "PHP", "Asia/Manila", "Philippine Airlines", "Cabin Crew"),
    ("Lucas", "Silva", "pt", "BRL", "America/Sao_Paulo", "LATAM", "Flight Engineer"),
    ("Amelie", "Dubois", "fr", "EUR", "Europe/Paris", "Air France", "Cabin Manager"),
    ("Kwame", "Mensah", "en", "GHS", "Africa/Accra", "Africa World Airlines", "Captain"),
    ("Emma", "Wilson", "en", "AUD", "Australia/Sydney", "Qantas", "First Officer"),
    ("Noah", "Mueller", "de", "EUR", "Europe/Berlin", "Lufthansa", "Purser"),
    ("Priya", "Sharma", "hi", "INR", "Asia/Kolkata", "Air India", "Cabin Crew"),
)

NETWORK_STATUSES = ("online", "offline", "activating", "suspended")
DEVICE_MODELS = ("iPhone 16 Pro", "Pixel 10", "Galaxy S26", "iPad Air", "Crew Router")
MOBILE_NETWORKS = (
    (310, 260),  # United States
    (222, 1),  # Italy
    (440, 10),  # Japan
    (515, 2),  # Philippines
    (724, 5),  # Brazil
    (208, 1),  # France
    (620, 1),  # Ghana
    (505, 1),  # Australia
    (262, 2),  # Germany
    (404, 45),  # India
)
USAGE_TYPES = (
    (1, "data"),
    (2, "voice"),
    (3, "sms"),
)
# Database columns use timezone-naive datetimes throughout the existing model.
SEED_START_DATE = datetime(2025, 1, 15, 8, 30)  # noqa: DTZ001


def build_seed_record(number: int) -> SeedRecord:
    """Build one deterministic, table-friendly user/eSIM fixture."""
    firstname, lastname, language, currency, timezone, airline, position = SEED_PROFILES[
        (number - 1) % len(SEED_PROFILES)
    ]
    cycle = (number - 1) // len(SEED_PROFILES)
    email_suffix = "" if cycle == 0 else str(number)
    createdate = SEED_START_DATE + timedelta(days=number * 3, hours=number % 12)

    return SeedRecord(
        email=f"{firstname.lower()}.{lastname.lower()}{email_suffix}@example.test",
        language=language,
        currency=currency,
        timezone=timezone,
        imsi=f"00101000000{number:04d}",
        firstname=firstname,
        lastname=lastname,
        airline=airline,
        position=position,
        referralcode=f"CREW{number:04d}",
        stripeid=f"cus_seed_{number:04d}",
        logtoid=f"logto_seed_{number:04d}",
        createdate=createdate,
        newsletter=number % 3 != 0,
        smsnotification=number % 2 == 0,
        rateus=createdate + timedelta(days=30) if number % 4 == 0 else None,
        esim_name=f"{firstname}'s {DEVICE_MODELS[(number - 1) % len(DEVICE_MODELS)]}",
        isesim=number % 5 != 0,
        esim_createdate=createdate + timedelta(hours=2),
        token=f"{number:08d}",
        networkstatus=NETWORK_STATUSES[(number - 1) % len(NETWORK_STATUSES)],
        balance=round(5.0 + number * 1.37, 2),
        use_account_for_charging=number % 3 == 0,
        smdpserver="rsp.example.test",
        activationcode=f"LPA:1$rsp.example.test$SEED{number:04d}",
        imei=f"3569380356{number:05d}",
        imei_device=DEVICE_MODELS[(number - 1) % len(DEVICE_MODELS)],
        allow_data=number % 7 != 0,
    )


SEED_RECORDS = tuple(build_seed_record(number) for number in range(1, 101))


def build_usage_seed_record(
    subscriber_number: int, event_number: int, seed: SeedRecord
) -> UsageSeedRecord:
    """Build one usage event linked to a deterministic seeded eSIM."""
    usage_type_id, usage_type = USAGE_TYPES[event_number]
    mcc, mnc = MOBILE_NETWORKS[(subscriber_number + event_number - 1) % len(MOBILE_NETWORKS)]
    usage_date = seed.esim_createdate + timedelta(
        days=event_number * 4 + subscriber_number % 7,
        hours=event_number * 3,
    )
    destination = None
    total_qty = 5_000_000 + subscriber_number * 73_421
    custo_charge = Decimal(total_qty) / Decimal(1_000_000_000)
    subs_charge = custo_charge * Decimal("1.35")
    down_bitrate = 50_000_000 + subscriber_number * 100_000
    up_bitrate = 10_000_000 + subscriber_number * 50_000

    if usage_type == "voice":
        destination = f"+1800555{subscriber_number:04d}"
        total_qty = 30 + subscriber_number % 271
        custo_charge = Decimal(total_qty) * Decimal("0.0025")
        subs_charge = Decimal(total_qty) * Decimal("0.0040")
        down_bitrate = 64_000
        up_bitrate = 64_000
    elif usage_type == "sms":
        destination = f"+4477009{subscriber_number:04d}"
        total_qty = 1 + subscriber_number % 3
        custo_charge = Decimal(total_qty) * Decimal("0.015")
        subs_charge = Decimal(total_qty) * Decimal("0.025")
        down_bitrate = 0
        up_bitrate = 0

    return UsageSeedRecord(
        usage_date_utc=usage_date,
        session_id=f"seed-{seed.imsi}-{event_number + 1}",
        mcc=mcc,
        mnc=mnc,
        total_qty=total_qty,
        usage_type_id=usage_type_id,
        usage_type=usage_type,
        dest_phone_number=destination,
        subs_reseller_name="CrewSim",
        custo_account_name="Seed account",
        subs_account_name=f"{seed.firstname} {seed.lastname}",
        subscriber_id=10_000 + subscriber_number,
        imsi=seed.imsi,
        iccid=f"8944700000000{subscriber_number:06d}",
        subs_phone_number=f"+63917{subscriber_number:07d}",
        prepaid_package_ids=str(100 + subscriber_number % 5),
        prepaid_package_qtys="1",
        toll_free="true" if usage_type == "voice" and subscriber_number % 4 == 0 else "false",
        custo_account_id=5_001,
        custo_charge=custo_charge.quantize(Decimal("0.000000000000001")),
        subs_account_id=6_000 + subscriber_number,
        subs_charge=subs_charge.quantize(Decimal("0.000000000000001")),
        apn="global.crewsim.test",
        rat=(4, 5, 6)[(subscriber_number + event_number) % 3],
        imei=seed.imei or f"3569380356{subscriber_number:05d}",
        down_bitrate=down_bitrate,
        up_bitrate=up_bitrate,
        filename=f"usage-{usage_date:%Y%m%d}.csv",
    )


SEED_USAGE_RECORDS = tuple(
    build_usage_seed_record(subscriber_number, event_number, seed)
    for subscriber_number, seed in enumerate(SEED_RECORDS, start=1)
    for event_number in range(len(USAGE_TYPES))
)


def seed_database(session: Session, records: Sequence[SeedRecord]) -> SeedResult:
    """Insert missing seed records in one transaction and leave existing data unchanged."""
    emails = [record.email for record in records]
    imsis = [record.imsi for record in records]
    requested_usage = [record for record in SEED_USAGE_RECORDS if record.imsi in imsis]
    session_ids = [record.session_id for record in requested_usage]

    created_users = 0
    created_esims = 0
    created_usage = 0

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
        existing_usage_session_ids = set(
            session.scalars(select(Usage.session_id).where(Usage.session_id.in_(session_ids)))
        )

        for record in records:
            user = users_by_email.get(record.email)
            if user is None:
                user = User(
                    email=record.email,
                    language=record.language,
                    currency=record.currency,
                    timezone=record.timezone,
                    firstname=record.firstname,
                    lastname=record.lastname,
                    airline=record.airline,
                    position=record.position,
                    referralcode=record.referralcode,
                    stripeid=record.stripeid,
                    logtoid=record.logtoid,
                    createdate=record.createdate,
                    newsletter=record.newsletter,
                    smsnotification=record.smsnotification,
                    rateus=record.rateus,
                )
                session.add(user)
                session.flush()
                users_by_email[record.email] = user
                created_users += 1

            esim = esims_by_imsi.get(record.imsi)
            if esim is None:
                esim = ESIM(
                    userid=user.id,
                    accountid=account.id,
                    imsi=record.imsi,
                    name=record.esim_name,
                    isesim=record.isesim,
                    createdate=record.esim_createdate,
                    token=record.token,
                    networkstatus=record.networkstatus,
                    balance=record.balance,
                    use_account_for_charging=record.use_account_for_charging,
                    smdpserver=record.smdpserver,
                    activationcode=record.activationcode,
                    imei=record.imei,
                    imei_device=record.imei_device,
                    allow_data=record.allow_data,
                )
                session.add(esim)
                esims_by_imsi[record.imsi] = esim
                created_esims += 1
            elif esim.userid != user.id:
                raise RuntimeError(
                    f"Seed IMSI {record.imsi} already belongs to user {esim.userid}, "
                    f"not {user.id} ({record.email})"
                )

        for record in requested_usage:
            if record.session_id in existing_usage_session_ids:
                continue

            session.add(Usage(**record.__dict__))
            existing_usage_session_ids.add(record.session_id)
            created_usage += 1

    return SeedResult(
        created_users=created_users,
        existing_users=len(records) - created_users,
        created_esims=created_esims,
        existing_esims=len(records) - created_esims,
        created_usage=created_usage,
        existing_usage=len(requested_usage) - created_usage,
    )


def parse_args() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--count",
        type=int,
        choices=range(1, 101),
        default=100,
        metavar="1-100",
        help="number of user/eSIM pairs to seed (default: 100)",
    )
    return parser


def main() -> None:
    args = parse_args().parse_args()
    with SessionLocal() as session:
        result = seed_database(session, SEED_RECORDS[: args.count])

    print(
        "Seed complete: "
        f"users {result.created_users} created/{result.existing_users} existing; "
        f"eSIMs {result.created_esims} created/{result.existing_esims} existing; "
        f"usage {result.created_usage} created/{result.existing_usage} existing."
    )


if __name__ == "__main__":
    main()

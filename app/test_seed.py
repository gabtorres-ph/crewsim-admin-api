from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.esims.models import ESIM
from app.seed import SEED_RECORDS, seed_database
from app.users.models import User


def test_seed_database_creates_requested_user_esim_pairs(db_session: Session):
    records = SEED_RECORDS[:5]

    result = seed_database(db_session, records)

    assert result.created_users == 5
    assert result.existing_users == 0
    assert result.created_esims == 5
    assert result.existing_esims == 0
    assert db_session.scalar(select(func.count()).select_from(User)) == 5
    assert db_session.scalar(select(func.count()).select_from(ESIM)) == 5
    stored_pairs = set(
        db_session.execute(
            select(User.email, ESIM.imsi).join(ESIM, ESIM.userid == User.id)
        ).tuples()
    )
    assert stored_pairs == {(record.email, record.imsi) for record in records}


def test_seed_database_is_repeatable(db_session: Session):
    records = SEED_RECORDS[:8]

    first_result = seed_database(db_session, records)
    second_result = seed_database(db_session, records)

    assert first_result.created_users == 8
    assert first_result.created_esims == 8
    assert second_result.created_users == 0
    assert second_result.existing_users == 8
    assert second_result.created_esims == 0
    assert second_result.existing_esims == 8
    assert db_session.scalar(select(func.count()).select_from(User)) == 8
    assert db_session.scalar(select(func.count()).select_from(ESIM)) == 8


def test_seed_records_support_dense_paginated_tables(db_session: Session):
    result = seed_database(db_session, SEED_RECORDS)

    assert len(SEED_RECORDS) == 100
    assert result.created_users == 100
    assert result.created_esims == 100
    assert len({record.email for record in SEED_RECORDS}) == 100
    assert len({record.imsi for record in SEED_RECORDS}) == 100

    user = db_session.scalar(select(User).where(User.email == SEED_RECORDS[-1].email))
    esim = db_session.scalar(select(ESIM).where(ESIM.imsi == SEED_RECORDS[-1].imsi))

    assert user is not None
    assert user.firstname == SEED_RECORDS[-1].firstname
    assert user.airline == SEED_RECORDS[-1].airline
    assert user.createdate == SEED_RECORDS[-1].createdate
    assert esim is not None
    assert esim.name == SEED_RECORDS[-1].esim_name
    assert esim.networkstatus == SEED_RECORDS[-1].networkstatus
    assert esim.imei_device == SEED_RECORDS[-1].imei_device

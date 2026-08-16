from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ESIM, User
from app.seed import SEED_RECORDS, seed_database


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

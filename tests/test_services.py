import pytest
from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.models import Account
from app.schemas.esims import ESIMCreate, ESIMUpdate
from app.services.esims import ESIMService
from app.users.manager import UserManager
from app.users.schemas import UserCreate


def make_user_data(email: str = "person@example.com") -> UserCreate:
    return UserCreate(
        email=email,
        language="en",
        currency="USD",
        timezone="UTC",
    )


def create_account(session: Session) -> Account:
    account = Account(name="Test account", balance=0)
    session.add(account)
    session.flush()
    return account


def test_esim_service_validates_user_and_can_reassign(db_session: Session):
    users = UserManager(db_session)
    esims = ESIMService(db_session)
    account = create_account(db_session)
    first_user = users.create_user(make_user_data())
    second_user = users.create_user(make_user_data("second@example.com"))

    esim = esims.create_esim(ESIMCreate(user_id=first_user.id, account_id=account.id, imsi="12345"))
    updated = esims.update_esim(esim.id, ESIMUpdate(user_id=second_user.id))

    assert updated.userid == second_user.id
    assert esims.list_esims(user_id=first_user.id) == []
    assert esims.list_esims(user_id=second_user.id) == [updated]


def test_esim_service_rejects_missing_user(db_session: Session):
    account = create_account(db_session)
    with pytest.raises(ResourceNotFoundError, match="User '999' was not found"):
        ESIMService(db_session).create_esim(
            ESIMCreate(user_id=999, account_id=account.id, imsi="12345")
        )

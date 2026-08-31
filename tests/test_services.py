import pytest
from sqlalchemy.orm import Session

from app.exceptions import ResourceConflictError, ResourceNotFoundError
from app.models import Account
from app.schemas.esims import ESIMCreate, ESIMUpdate
from app.schemas.users import UserCreate
from app.services.esims import ESIMService
from app.services.users import UserService


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
    users = UserService(db_session)
    esims = ESIMService(db_session)
    account = create_account(db_session)
    first_user = users.create_user(make_user_data())
    second_user = users.create_user(make_user_data("second@example.com"))

    esim = esims.create_esim(
        ESIMCreate(user_id=first_user.id, account_id=account.id, imsi="12345")
    )
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


def test_user_service_returns_conflict_for_duplicate_email(db_session: Session):
    users = UserService(db_session)
    users.create_user(make_user_data())

    with pytest.raises(ResourceConflictError):
        users.create_user(make_user_data())


def test_user_delete_rolls_back_when_esim_references_user(db_session: Session):
    users = UserService(db_session)
    esims = ESIMService(db_session)
    account = create_account(db_session)
    user = users.create_user(make_user_data())
    esims.create_esim(ESIMCreate(user_id=user.id, account_id=account.id, imsi="12345"))

    with pytest.raises(ResourceConflictError):
        users.delete_user(user.id)

    assert users.get_user(user.id).email == "person@example.com"

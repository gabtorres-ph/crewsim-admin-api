from sqlalchemy.orm import Session

from app.models import Account
from app.repositories.esims import ESIMRepository
from app.repositories.users import UserRepository


def test_user_repository_crud_and_lookup(db_session: Session):
    repository = UserRepository(db_session)
    first = repository.create(
        {
            "email": "one@example.com",
            "language": "en",
            "currency": "USD",
            "timezone": "UTC",
        }
    )
    second = repository.create(
        {
            "email": "two@example.com",
            "language": "fr",
            "currency": "EUR",
            "timezone": "Europe/Paris",
        }
    )

    assert repository.get(first.id) is first
    assert repository.get_by_email("one@example.com") is first
    assert repository.list(offset=1, limit=1) == [second]

    repository.update(first, {"language": "es"})
    assert first.language == "es"

    repository.delete(second)
    assert repository.get(second.id) is None


def test_esim_repository_lookup_and_user_filter(db_session: Session):
    users = UserRepository(db_session)
    esims = ESIMRepository(db_session)
    account = Account(name="Test account", balance=0)
    db_session.add(account)
    db_session.flush()
    user = users.create(
        {
            "email": "owner@example.com",
            "language": "en",
            "currency": "USD",
            "timezone": "UTC",
        }
    )
    other_user = users.create(
        {
            "email": "other@example.com",
            "language": "en",
            "currency": "USD",
            "timezone": "UTC",
        }
    )
    owned_esim = esims.create({"userid": user.id, "accountid": account.id, "imsi": "00101"})
    esims.create({"userid": other_user.id, "accountid": account.id, "imsi": "00102"})

    assert esims.get_by_imsi("00101") is owned_esim
    assert esims.list_for_user(user.id) == [owned_esim]

from sqlalchemy.orm import Session

from app.models import Account
from app.repositories.esims import ESIMRepository
from app.users.resource_access import UserResourceAccess


def test_esim_repository_lookup_and_user_filter(db_session: Session):
    users = UserResourceAccess(db_session)
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

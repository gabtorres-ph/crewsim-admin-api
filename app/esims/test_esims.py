import pytest
from sqlalchemy.orm import Session

from app.accounts.models import Account
from app.common.exceptions import ResourceNotFoundError
from app.esims.manager import ESIMManager
from app.esims.resource_access import ESIMResourceAccess
from app.esims.schemas import ESIMCreate, ESIMUpdate
from app.users.manager import UserManager
from app.users.resource_access import UserResourceAccess
from app.users.schemas import UserCreate


def user_payload(email: str = "person@example.com") -> dict[str, str]:
    return {
        "email": email,
        "language": "en",
        "currency": "USD",
        "timezone": "UTC",
    }


def create_account(session: Session, name: str = "Test account") -> Account:
    account = Account(name=name, balance=0)
    session.add(account)
    session.flush()
    return account


def test_esim_resource_access_lookup_and_filters(db_session: Session) -> None:
    users = UserResourceAccess(db_session)
    esims = ESIMResourceAccess(db_session)
    account = create_account(db_session)
    other_account = create_account(db_session, "Other account")
    user = users.create(user_payload("owner@example.com"))
    other_user = users.create(user_payload("other@example.com"))
    owned_esim = esims.create({"userid": user.id, "accountid": account.id, "imsi": "00101"})
    account_esim = esims.create(
        {"userid": other_user.id, "accountid": account.id, "imsi": "00102"}
    )
    esims.create({"userid": other_user.id, "accountid": other_account.id, "imsi": "00103"})

    assert esims.get_by_imsi("00101") is owned_esim
    assert esims.list_for_user(user.id) == [owned_esim]
    assert esims.list_for_account(account.id) == [owned_esim, account_esim]
    assert esims.list_for_account(account.id, offset=1, limit=1) == [account_esim]


def test_esim_manager_validates_references_and_can_reassign(db_session: Session) -> None:
    users = UserManager(db_session)
    esims = ESIMManager(db_session)
    account = create_account(db_session)
    first_user = users.create_user(UserCreate(**user_payload()))
    second_user = users.create_user(UserCreate(**user_payload("second@example.com")))

    esim = esims.create_esim(
        ESIMCreate(user_id=first_user.id, account_id=account.id, imsi="12345")
    )
    updated = esims.update_esim(esim.id, ESIMUpdate(user_id=second_user.id))

    assert updated.userid == second_user.id
    assert esims.list_esims(user_id=first_user.id) == []
    assert esims.list_esims(user_id=second_user.id) == [updated]

    with pytest.raises(ResourceNotFoundError, match="User '999' was not found"):
        esims.create_esim(ESIMCreate(user_id=999, account_id=account.id, imsi="54321"))

    with pytest.raises(ResourceNotFoundError, match="Account '999' was not found"):
        esims.create_esim(ESIMCreate(account_id=999, imsi="54321"))


@pytest.mark.asyncio
async def test_esim_crud_filters_nested_listing_and_public_field_names(client) -> None:
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]
    account_id = (
        await client.post("/api/accounts", json={"name": "Test account", "balance": 0})
    ).json()["id"]
    create_response = await client.post(
        "/api/esims",
        json={"user_id": user_id, "account_id": account_id, "imsi": "001010000000001"},
    )
    assert create_response.status_code == 201
    esim = create_response.json()
    assert esim["user_id"] == user_id
    assert esim["account_id"] == account_id
    assert "userid" not in esim
    assert "accountid" not in esim

    assert (await client.get(f"/api/esims/{esim['id']}")).json() == esim
    assert (await client.get(f"/api/users/{user_id}/esims")).json() == [esim]
    assert (await client.get(f"/api/accounts/{account_id}/esims")).json() == [esim]
    assert (await client.get(f"/api/esims?user_id={user_id}")).json() == [esim]

    update_response = await client.patch(f"/api/esims/{esim['id']}", json={"imsi": "00202"})
    assert update_response.status_code == 200
    assert update_response.json()["imsi"] == "00202"

    assert (await client.delete(f"/api/esims/{esim['id']}")).status_code == 204
    assert (await client.get(f"/api/esims/{esim['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_esim_routes_reject_missing_user_and_account_independently(client) -> None:
    account_id = (
        await client.post("/api/accounts", json={"name": "Test account", "balance": 0})
    ).json()["id"]

    missing_user = await client.post(
        "/api/esims", json={"user_id": 999, "account_id": account_id, "imsi": "00101"}
    )
    assert missing_user.status_code == 404
    assert missing_user.json() == {"detail": "User '999' was not found"}

    missing_account = await client.post(
        "/api/esims", json={"account_id": 999, "imsi": "00101"}
    )
    assert missing_account.status_code == 404
    assert missing_account.json() == {"detail": "Account '999' was not found"}

    assert (await client.get("/api/users/999/esims")).status_code == 404
    assert (await client.get("/api/accounts/999/esims")).status_code == 404

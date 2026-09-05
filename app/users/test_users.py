import pytest
from sqlalchemy.orm import Session

from app.accounts.models import Account
from app.common.exceptions import ResourceConflictError
from app.esims.manager import ESIMManager
from app.esims.schemas import ESIMCreate
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


def make_user_data(email: str = "person@example.com") -> UserCreate:
    return UserCreate(**user_payload(email))


def create_account(session: Session) -> Account:
    account = Account(name="Test account", balance=0)
    session.add(account)
    session.flush()
    return account


def test_user_resource_access_crud_and_lookup(db_session: Session) -> None:
    users = UserResourceAccess(db_session)
    first = users.create(user_payload("one@example.com"))
    second = users.create(
        {
            "email": "two@example.com",
            "language": "fr",
            "currency": "EUR",
            "timezone": "Europe/Paris",
        }
    )

    assert users.get(first.id) is first
    assert users.get_by_email("one@example.com") is first
    assert users.list(offset=1, limit=1) == [second]

    users.update(first, {"language": "es"})
    assert first.language == "es"

    users.delete(second)
    assert users.get(second.id) is None


def test_user_manager_returns_conflict_for_duplicate_email(db_session: Session) -> None:
    users = UserManager(db_session)
    users.create_user(make_user_data())

    with pytest.raises(ResourceConflictError):
        users.create_user(make_user_data())


def test_user_delete_rolls_back_when_esim_references_user(db_session: Session) -> None:
    users = UserManager(db_session)
    esims = ESIMManager(db_session)
    account = create_account(db_session)
    user = users.create_user(make_user_data())
    esims.create_esim(ESIMCreate(user_id=user.id, account_id=account.id, imsi="12345"))

    with pytest.raises(ResourceConflictError):
        users.delete_user(user.id)

    assert users.get_user(user.id).email == "person@example.com"


@pytest.mark.asyncio
async def test_user_crud(client) -> None:
    create_response = await client.post("/api/users", json=user_payload())
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    assert (await client.get(f"/api/users/{user_id}")).json()["email"] == "person@example.com"
    assert (await client.get("/api/users")).json() == [create_response.json()]

    update_response = await client.patch(f"/api/users/{user_id}", json={"currency": "EUR"})
    assert update_response.status_code == 200
    assert update_response.json()["currency"] == "EUR"

    assert (await client.delete(f"/api/users/{user_id}")).status_code == 204
    assert (await client.get(f"/api/users/{user_id}")).status_code == 404


@pytest.mark.asyncio
async def test_duplicate_user_email_returns_conflict(client) -> None:
    assert (await client.post("/api/users", json=user_payload())).status_code == 201

    response = await client.post("/api/users", json=user_payload())

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_user_with_favorite_cannot_be_deleted(client) -> None:
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]
    assert (
        await client.post("/api/favorites", json={"user_id": user_id, "country": "Japan"})
    ).status_code == 201

    response = await client.delete(f"/api/users/{user_id}")

    assert response.status_code == 409
    assert (await client.get(f"/api/users/{user_id}")).status_code == 200


@pytest.mark.asyncio
async def test_user_with_esim_cannot_be_deleted(client, db_session: Session) -> None:
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]
    account = create_account(db_session)
    await client.post(
        "/api/esims", json={"user_id": user_id, "account_id": account.id, "imsi": "00101"}
    )

    response = await client.delete(f"/api/users/{user_id}")

    assert response.status_code == 409
    assert (await client.get(f"/api/users/{user_id}")).status_code == 200


@pytest.mark.asyncio
async def test_partial_updates_reject_null_and_list_limits_are_validated(client) -> None:
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]

    null_response = await client.patch(f"/api/users/{user_id}", json={"email": None})
    assert null_response.status_code == 422
    assert (await client.get("/api/users?limit=101")).status_code == 422

import pytest

from app.models import Account


def user_payload(email="person@example.com"):
    return {
        "email": email,
        "language": "en",
        "currency": "USD",
        "timezone": "UTC",
    }


def create_account(db_session):
    account = Account(name="Test account", balance=0)
    db_session.add(account)
    db_session.flush()
    return account


@pytest.mark.asyncio
async def test_user_crud(client):
    create_response = await client.post("/api/users", json=user_payload())
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    assert (await client.get(f"/api/users/{user_id}")).json()["email"] == "person@example.com"
    assert (await client.get("/api/users")).json() == [create_response.json()]

    update_response = await client.patch(f"/api/users/{user_id}", json={"currency": "EUR"})
    assert update_response.status_code == 200
    assert update_response.json()["currency"] == "EUR"

    delete_response = await client.delete(f"/api/users/{user_id}")
    assert delete_response.status_code == 204
    assert (await client.get(f"/api/users/{user_id}")).status_code == 404


@pytest.mark.asyncio
async def test_account_crud_and_esim_listing(client):
    create_response = await client.post(
        "/api/accounts", json={"name": "Test account", "balance": 12.5}
    )
    assert create_response.status_code == 201
    account = create_response.json()
    account_id = account["id"]

    assert (await client.get(f"/api/accounts/{account_id}")).json() == account
    assert (await client.get("/api/accounts")).json() == [account]

    update_response = await client.patch(
        f"/api/accounts/{account_id}", json={"balance": 20}
    )
    assert update_response.status_code == 200
    assert update_response.json()["balance"] == 20

    esim = (
        await client.post(
            "/api/esims", json={"account_id": account_id, "imsi": "001010000000001"}
        )
    ).json()
    assert (await client.get(f"/api/accounts/{account_id}/esims")).json() == [esim]

    assert (await client.delete(f"/api/accounts/{account_id}")).status_code == 409
    assert (await client.delete(f"/api/esims/{esim['id']}")).status_code == 204
    assert (await client.delete(f"/api/accounts/{account_id}")).status_code == 204
    assert (await client.get(f"/api/accounts/{account_id}")).status_code == 404


@pytest.mark.asyncio
async def test_esim_crud_and_user_filter(client, db_session):
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]
    account = create_account(db_session)
    create_response = await client.post(
        "/api/esims",
        json={"user_id": user_id, "account_id": account.id, "imsi": "001010000000001"},
    )
    assert create_response.status_code == 201
    esim = create_response.json()
    assert esim["user_id"] == user_id

    assert (await client.get(f"/api/esims/{esim['id']}")).json() == esim
    assert (await client.get(f"/api/users/{user_id}/esims")).json() == [esim]
    assert (await client.get(f"/api/esims?user_id={user_id}")).json() == [esim]

    update_response = await client.patch(
        f"/api/esims/{esim['id']}", json={"imsi": "00202"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["imsi"] == "00202"

    assert (await client.delete(f"/api/esims/{esim['id']}")).status_code == 204
    assert (await client.get(f"/api/esims/{esim['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_esim_requires_existing_user(client, db_session):
    account = create_account(db_session)
    response = await client.post(
        "/api/esims", json={"user_id": 999, "account_id": account.id, "imsi": "00101"}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "User '999' was not found"}


@pytest.mark.asyncio
async def test_favorite_crud_and_user_filters(client):
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]
    create_response = await client.post(
        "/api/favorites", json={"user_id": user_id, "country": "Japan"}
    )
    assert create_response.status_code == 201
    favorite = create_response.json()
    assert favorite["user_id"] == user_id
    assert favorite["country"] == "Japan"

    assert (await client.get(f"/api/favorites/{favorite['id']}")).json() == favorite
    assert (await client.get(f"/api/favorites?user_id={user_id}")).json() == [favorite]
    assert (await client.get(f"/api/users/{user_id}/favorites")).json() == [favorite]

    assert (await client.delete(f"/api/favorites/{favorite['id']}")).status_code == 204
    assert (await client.get(f"/api/favorites/{favorite['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_favorite_duplicate_and_missing_resource_handling(client):
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]
    payload = {"user_id": user_id, "country": "Japan"}
    assert (await client.post("/api/favorites", json=payload)).status_code == 201

    duplicate_response = await client.post("/api/favorites", json=payload)
    assert duplicate_response.status_code == 409

    second_user_id = (
        await client.post("/api/users", json=user_payload("second@example.com"))
    ).json()["id"]
    assert (
        await client.post(
            "/api/favorites", json={"user_id": second_user_id, "country": "Japan"}
        )
    ).status_code == 201

    missing_user_response = await client.post(
        "/api/favorites", json={"user_id": 999, "country": "Japan"}
    )
    assert missing_user_response.status_code == 404
    assert (await client.get("/api/favorites/999")).status_code == 404
    assert (await client.get("/api/favorites?user_id=999")).status_code == 404
    assert (await client.get("/api/users/999/favorites")).status_code == 404
    assert (await client.get("/api/favorites?limit=101")).status_code == 422
    assert (await client.get("/api/favorites?user_id=0")).status_code == 422


@pytest.mark.asyncio
async def test_user_with_favorite_cannot_be_deleted(client):
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]
    assert (
        await client.post("/api/favorites", json={"user_id": user_id, "country": "Japan"})
    ).status_code == 201

    response = await client.delete(f"/api/users/{user_id}")

    assert response.status_code == 409
    assert (await client.get(f"/api/users/{user_id}")).status_code == 200


@pytest.mark.asyncio
async def test_duplicate_user_email_returns_conflict(client):
    assert (await client.post("/api/users", json=user_payload())).status_code == 201

    response = await client.post("/api/users", json=user_payload())

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_user_with_esim_cannot_be_deleted(client, db_session):
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]
    account = create_account(db_session)
    await client.post(
        "/api/esims", json={"user_id": user_id, "account_id": account.id, "imsi": "00101"}
    )

    response = await client.delete(f"/api/users/{user_id}")

    assert response.status_code == 409
    assert (await client.get(f"/api/users/{user_id}")).status_code == 200


@pytest.mark.asyncio
async def test_partial_updates_reject_null_and_list_limits_are_validated(client):
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]

    null_response = await client.patch(f"/api/users/{user_id}", json={"email": None})
    assert null_response.status_code == 422
    assert (await client.get("/api/users?limit=101")).status_code == 422

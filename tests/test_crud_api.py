import pytest


def user_payload(email="person@example.com"):
    return {
        "email": email,
        "language": "en",
        "currency": "USD",
        "timezone": "UTC",
    }


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
async def test_esim_crud_and_user_filter(client):
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]
    create_response = await client.post(
        "/api/esims", json={"user_id": user_id, "imsi": "001010000000001"}
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
async def test_esim_requires_existing_user(client):
    response = await client.post("/api/esims", json={"user_id": 999, "imsi": "00101"})

    assert response.status_code == 404
    assert response.json() == {"detail": "User '999' was not found"}


@pytest.mark.asyncio
async def test_duplicate_user_email_returns_conflict(client):
    assert (await client.post("/api/users", json=user_payload())).status_code == 201

    response = await client.post("/api/users", json=user_payload())

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_user_with_esim_cannot_be_deleted(client):
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]
    await client.post("/api/esims", json={"user_id": user_id, "imsi": "00101"})

    response = await client.delete(f"/api/users/{user_id}")

    assert response.status_code == 409
    assert (await client.get(f"/api/users/{user_id}")).status_code == 200


@pytest.mark.asyncio
async def test_partial_updates_reject_null_and_list_limits_are_validated(client):
    user_id = (await client.post("/api/users", json=user_payload())).json()["id"]

    null_response = await client.patch(f"/api/users/{user_id}", json={"email": None})
    assert null_response.status_code == 422
    assert (await client.get("/api/users?limit=101")).status_code == 422

import pytest


def user_payload(email="person@example.com"):
    return {
        "email": email,
        "language": "en",
        "currency": "USD",
        "timezone": "UTC",
    }
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
        await client.post("/api/favorites", json={"user_id": second_user_id, "country": "Japan"})
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

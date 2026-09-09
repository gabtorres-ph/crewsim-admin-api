import pytest
from sqlalchemy.orm import Session

from app.common.exceptions import ResourceConflictError, ResourceNotFoundError
from app.email.manager import EmailWhitelistManager
from app.email.models import EmailWhitelist
from app.email.resource_access import EmailWhitelistResourceAccess
from app.email.schemas import EmailWhitelistCreate, EmailWhitelistUpdate


def whitelist_payload(
    email: str = "person@example.com", status: str = "active"
) -> dict[str, str]:
    return {"email": email, "status": status}


def make_whitelist_data(
    email: str = "person@example.com", status: str = "active"
) -> EmailWhitelistCreate:
    return EmailWhitelistCreate(**whitelist_payload(email, status))


def test_email_whitelist_resource_access_crud_lookup_and_pagination(
    db_session: Session,
) -> None:
    email_whitelist = EmailWhitelistResourceAccess(db_session)
    first = email_whitelist.create(whitelist_payload("one@example.com"))
    second = email_whitelist.create(whitelist_payload("two@example.com", "pending"))
    third = email_whitelist.create(whitelist_payload("three@example.com"))

    assert email_whitelist.get(first.id) is first
    assert email_whitelist.get_by_email("one@example.com") is first
    assert email_whitelist.list(offset=1, limit=1) == [second]
    assert email_whitelist.list(offset=2, limit=10) == [third]

    email_whitelist.update(first, {"status": "inactive"})
    assert first.status == "inactive"

    email_whitelist.delete(third)
    assert email_whitelist.get(third.id) is None


def test_email_whitelist_manager_crud_and_commits(db_session: Session) -> None:
    manager = EmailWhitelistManager(db_session)
    email_whitelist = manager.create_email_whitelist(make_whitelist_data())

    assert email_whitelist.createdate is not None
    with Session(db_session.get_bind()) as other_session:
        assert other_session.get(EmailWhitelist, email_whitelist.id) is not None

    updated = manager.update_email_whitelist(
        email_whitelist.id,
        EmailWhitelistUpdate(email="updated@example.com", status="inactive"),
    )
    assert updated.email == "updated@example.com"
    assert updated.status == "inactive"

    manager.delete_email_whitelist(email_whitelist.id)
    with pytest.raises(
        ResourceNotFoundError,
        match=f"EmailWhitelist '{email_whitelist.id}' was not found",
    ):
        manager.get_email_whitelist(email_whitelist.id)


def test_email_whitelist_manager_returns_conflict_for_duplicate_email(
    db_session: Session,
) -> None:
    manager = EmailWhitelistManager(db_session)
    manager.create_email_whitelist(make_whitelist_data())

    with pytest.raises(ResourceConflictError):
        manager.create_email_whitelist(make_whitelist_data())


@pytest.mark.asyncio
async def test_email_whitelist_crud_pagination_and_response_shape(client) -> None:
    first_response = await client.post(
        "/api/email-whitelist",
        json=whitelist_payload(),
    )
    assert first_response.status_code == 201
    first = first_response.json()
    assert first == {
        "id": first["id"],
        "email": "person@example.com",
        "createdate": first["createdate"],
        "status": "active",
    }
    assert first["createdate"] is not None

    second_response = await client.post(
        "/api/email-whitelist",
        json=whitelist_payload("second@example.com", "pending"),
    )
    assert second_response.status_code == 201
    second = second_response.json()

    assert (await client.get(f"/api/email-whitelist/{first['id']}")).json() == first
    assert (await client.get("/api/email-whitelist?offset=1&limit=1")).json() == [second]

    update_response = await client.patch(
        f"/api/email-whitelist/{first['id']}",
        json={"email": "updated@example.com", "status": "inactive"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["email"] == "updated@example.com"
    assert updated["status"] == "inactive"
    assert updated["createdate"] == first["createdate"]

    assert (await client.delete(f"/api/email-whitelist/{first['id']}")).status_code == 204
    assert (await client.get(f"/api/email-whitelist/{first['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_email_whitelist_routes_handle_conflicts_and_validation(client) -> None:
    assert (await client.post("/api/email-whitelist", json=whitelist_payload())).status_code == 201

    duplicate_response = await client.post(
        "/api/email-whitelist",
        json=whitelist_payload(),
    )
    assert duplicate_response.status_code == 409

    assert (await client.post("/api/email-whitelist", json={})).status_code == 422
    assert (
        await client.post(
            "/api/email-whitelist",
            json=whitelist_payload("   ", "active"),
        )
    ).status_code == 422
    assert (
        await client.patch(
            "/api/email-whitelist/1",
            json={"email": None},
        )
    ).status_code == 422
    assert (await client.get("/api/email-whitelist/0")).status_code == 422
    assert (await client.get("/api/email-whitelist?offset=-1")).status_code == 422
    assert (await client.get("/api/email-whitelist?limit=0")).status_code == 422
    assert (await client.get("/api/email-whitelist?limit=101")).status_code == 422

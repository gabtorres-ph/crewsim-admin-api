import pytest
from sqlalchemy.orm import Session

from app.common.exceptions import ResourceConflictError, ResourceNotFoundError
from app.language.manager import LanguageManager
from app.language.models import Language
from app.language.resource_access import LanguageResourceAccess
from app.language.schemas import LanguageCreate, LanguageUpdate


def test_resource_access_crud_and_pagination(db_session: Session) -> None:
    access = LanguageResourceAccess(db_session)
    first = access.create({"iso3": "eng", "name": "English"})
    second = access.create({"iso3": "fra", "name": "French"})
    assert access.get(first.id) is first
    assert access.list(offset=1, limit=1) == [second]

    access.update(first, {"iso1": "en"})
    assert first.iso1 == "en"
    access.delete(second)
    assert access.get(second.id) is None


def test_manager_commits_nullable_updates_and_deletes(db_session: Session) -> None:
    manager = LanguageManager(db_session)
    language = manager.create_language(
        LanguageCreate(iso1="en", iso2b="eng", iso2t="eng", iso3="eng", name="English")
    )
    with Session(db_session.get_bind()) as other_session:
        assert other_session.get(Language, language.id) is not None

    updated = manager.update_language(
        language.id, LanguageUpdate(iso1=None, iso2b=None, iso2t=None, name="Modern English")
    )
    assert (updated.iso1, updated.iso2b, updated.iso2t) == (None, None, None)
    assert updated.iso3 == "eng"
    assert updated.name == "Modern English"

    manager.delete_language(language.id)
    with pytest.raises(ResourceNotFoundError, match=f"Language '{language.id}' was not found"):
        manager.get_language(language.id)


def test_manager_rolls_back_unique_code_conflicts(db_session: Session) -> None:
    manager = LanguageManager(db_session)
    first = manager.create_language(LanguageCreate(iso1="en", iso3="eng", name="English"))
    with pytest.raises(ResourceConflictError, match="language conflicts"):
        manager.create_language(LanguageCreate(iso1="en", iso3="fra", name="French"))
    assert manager.list_languages() == [first]

    second = manager.create_language(LanguageCreate(iso1="fr", iso3="fra", name="French"))
    with pytest.raises(ResourceConflictError, match="language update conflicts"):
        manager.update_language(second.id, LanguageUpdate(iso3="eng"))
    assert manager.get_language(second.id).iso3 == "fra"


@pytest.mark.asyncio
async def test_language_routes_crud_and_pagination(client) -> None:
    response = await client.post(
        "/api/languages",
        json={"iso1": "en", "iso2b": "eng", "iso2t": "eng", "iso3": "eng", "name": "English"},
    )
    assert response.status_code == 201
    first = response.json()
    assert first == {
        "id": first["id"],
        "iso1": "en",
        "iso2b": "eng",
        "iso2t": "eng",
        "iso3": "eng",
        "name": "English",
    }

    response = await client.post("/api/languages", json={"iso3": "fra", "name": "French"})
    assert response.status_code == 201
    second = response.json()
    assert second == {
        "id": second["id"],
        "iso1": None,
        "iso2b": None,
        "iso2t": None,
        "iso3": "fra",
        "name": "French",
    }
    assert (await client.get(f"/api/languages/{first['id']}")).json() == first
    assert (await client.get("/api/languages?offset=1&limit=1")).json() == [second]

    response = await client.patch(
        f"/api/languages/{first['id']}", json={"iso1": None, "name": "Modern English"}
    )
    assert response.status_code == 200
    assert response.json() == {**first, "iso1": None, "name": "Modern English"}

    assert (await client.delete(f"/api/languages/{first['id']}")).status_code == 204
    assert (await client.get(f"/api/languages/{first['id']}")).status_code == 404
    assert (await client.patch(f"/api/languages/{first['id']}", json={})).status_code == 404
    assert (await client.delete(f"/api/languages/{first['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_language_routes_validate_payloads_and_parameters(client) -> None:
    invalid_creates = (
        {},
        {"iso3": "en", "name": "English"},
        {"iso3": "eng", "name": "  "},
        {"iso1": "e", "iso3": "eng", "name": "English"},
        {"iso2b": "en", "iso3": "eng", "name": "English"},
        {"iso2t": "english", "iso3": "eng", "name": "English"},
        {"iso3": "eng", "name": "a" * 151},
    )
    for payload in invalid_creates:
        assert (await client.post("/api/languages", json=payload)).status_code == 422

    language = (
        await client.post("/api/languages", json={"iso3": "eng", "name": "English"})
    ).json()
    for payload in ({"iso3": None}, {"name": None}, {"iso1": "e"}):
        assert (
            await client.patch(f"/api/languages/{language['id']}", json=payload)
        ).status_code == 422

    assert (
        await client.post("/api/languages", json={"iso3": "eng", "name": "Duplicate"})
    ).status_code == 409
    assert (await client.get("/api/languages/0")).status_code == 422
    assert (await client.get("/api/languages?offset=-1")).status_code == 422
    assert (await client.get("/api/languages?limit=0")).status_code == 422
    assert (await client.get("/api/languages?limit=101")).status_code == 422

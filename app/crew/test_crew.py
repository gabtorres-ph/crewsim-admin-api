from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.common.exceptions import ResourceConflictError, ResourceNotFoundError
from app.crew.manager import CrewManager
from app.crew.models import Crew
from app.crew.resource_access import CrewResourceAccess
from app.crew.schemas import CrewCreate, CrewUpdate


def crew_values(**overrides):
    values = {
        "unique_id": "crew-1",
        "file1": "front.jpg",
        "file2": "back.jpg",
        "firstname": "Maria",
        "lastname": "Santos",
        "airline": "Philippine Airlines",
        "iscrewid": True,
        "createdate": datetime.fromisoformat("2026-09-07T08:30:00"),
        "user_id": 1001,
        "file1_hash": "a" * 64,
        "file2_hash": "b" * 64,
        "reason": "Matching crew identification",
        "confidence": Decimal("98.50"),
        "type": "airline-id",
        "dhash": "c" * 32,
        "phash": "d" * 32,
        "dhash_distance": 2,
        "phash_distance": 3,
    }
    values.update(overrides)
    return values


def crew_database_values(**overrides):
    values = crew_values(**overrides)
    values["userid"] = values.pop("user_id")
    return values


def crew_json(**overrides):
    values = crew_values(**overrides)
    values["createdate"] = values["createdate"].isoformat()
    if values["confidence"] is not None:
        values["confidence"] = str(values["confidence"])
    return values


def test_crew_resource_access_crud_and_pagination(db_session: Session) -> None:
    records = CrewResourceAccess(db_session)
    first = records.create(crew_database_values())
    second = records.create(crew_database_values(unique_id="crew-2"))
    third = records.create(crew_database_values(unique_id="crew-3"))

    assert records.get(first.id) is first
    assert records.list(offset=1, limit=1) == [second]
    assert records.list(offset=2, limit=10) == [third]

    records.update(first, {"reason": "Manual review", "confidence": Decimal("75.25")})
    assert first.reason == "Manual review"
    assert first.confidence == Decimal("75.25")

    records.delete(third)
    assert records.get(third.id) is None


def test_crew_manager_crud_nullable_update_and_commits(db_session: Session) -> None:
    manager = CrewManager(db_session)
    record = manager.create_crew(CrewCreate(**crew_values()))

    with Session(db_session.get_bind()) as other_session:
        persisted = other_session.get(Crew, record.id)
        assert persisted is not None
        assert persisted.userid == 1001

    updated = manager.update_crew(
        record.id,
        CrewUpdate(file1=None, user_id=None, reason=None, confidence=None),
    )
    assert updated.unique_id == "crew-1"
    assert updated.file1 is None
    assert updated.userid is None
    assert updated.reason is None
    assert updated.confidence is None

    manager.delete_crew(record.id)
    with pytest.raises(ResourceNotFoundError, match=f"Crew '{record.id}' was not found"):
        manager.get_crew(record.id)


def test_crew_manager_rolls_back_database_conflicts(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = CrewManager(db_session)

    def create_invalid_crew(values) -> Crew:
        record = Crew()
        db_session.add(record)
        db_session.flush()
        return record

    monkeypatch.setattr(manager.crew, "create", create_invalid_crew)

    with pytest.raises(ResourceConflictError, match="crew record conflicts"):
        manager.create_crew(CrewCreate(**crew_values()))

    assert manager.list_crew() == []


@pytest.mark.asyncio
async def test_crew_crud_pagination_and_response_shape(client) -> None:
    first_response = await client.post("/api/crew", json=crew_json())
    assert first_response.status_code == 201
    first = first_response.json()
    assert first == {"id": first["id"], **crew_json()}

    second_response = await client.post(
        "/api/crew",
        json=crew_json(
            unique_id="crew-2",
            file2=None,
            user_id=None,
            confidence=None,
            dhash_distance=None,
            phash_distance=None,
        ),
    )
    assert second_response.status_code == 201
    second = second_response.json()

    assert (await client.get(f"/api/crew/{first['id']}")).json() == first
    assert (await client.get("/api/crew?offset=1&limit=1")).json() == [second]

    update_response = await client.patch(
        f"/api/crew/{first['id']}",
        json={"file1": None, "user_id": None, "reason": None, "confidence": "75.25"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["file1"] is None
    assert updated["user_id"] is None
    assert updated["reason"] is None
    assert updated["confidence"] == "75.25"
    assert updated["unique_id"] == "crew-1"

    assert (await client.delete(f"/api/crew/{first['id']}")).status_code == 204
    assert (await client.get(f"/api/crew/{first['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_crew_routes_validate_payloads_and_parameters(client) -> None:
    assert (await client.post("/api/crew", json={})).status_code == 422
    assert (
        await client.post("/api/crew", json=crew_json(unique_id="  "))
    ).status_code == 422
    assert (
        await client.post("/api/crew", json=crew_json(file1="x" * 101))
    ).status_code == 422
    assert (
        await client.post("/api/crew", json=crew_json(firstname="x" * 151))
    ).status_code == 422
    assert (
        await client.post("/api/crew", json=crew_json(file1_hash="x" * 65))
    ).status_code == 422
    assert (
        await client.post("/api/crew", json=crew_json(reason="x" * 256))
    ).status_code == 422
    assert (
        await client.post("/api/crew", json=crew_json(dhash="x" * 33))
    ).status_code == 422
    assert (
        await client.post("/api/crew", json=crew_json(user_id=0))
    ).status_code == 422
    assert (
        await client.post("/api/crew", json=crew_json(confidence="123456789.12"))
    ).status_code == 422

    record = (await client.post("/api/crew", json=crew_json())).json()
    for field in ("unique_id", "iscrewid", "createdate"):
        assert (
            await client.patch(f"/api/crew/{record['id']}", json={field: None})
        ).status_code == 422

    nullable_response = await client.patch(
        f"/api/crew/{record['id']}",
        json={"file2": None, "user_id": None, "confidence": None},
    )
    assert nullable_response.status_code == 200
    assert nullable_response.json()["file2"] is None
    assert nullable_response.json()["user_id"] is None
    assert nullable_response.json()["confidence"] is None

    assert (await client.get("/api/crew/0")).status_code == 422
    assert (await client.get("/api/crew?offset=-1")).status_code == 422
    assert (await client.get("/api/crew?limit=0")).status_code == 422
    assert (await client.get("/api/crew?limit=101")).status_code == 422


def test_crew_model_preserves_table_columns_and_indexes() -> None:
    table = Crew.__table__

    assert table.name == "crewid"
    assert set(table.columns.keys()) == {
        "id",
        "unique_id",
        "file1",
        "file2",
        "firstname",
        "lastname",
        "airline",
        "iscrewid",
        "createdate",
        "userid",
        "file1_hash",
        "file2_hash",
        "reason",
        "confidence",
        "type",
        "dhash",
        "phash",
        "dhash_distance",
        "phash_distance",
    }
    assert table.c.unique_id.nullable is False
    assert table.c.iscrewid.nullable is False
    assert table.c.createdate.nullable is False
    assert table.c.file1.nullable is True
    assert table.c.confidence.type.precision == 10
    assert table.c.confidence.type.scale == 2
    assert {index.name for index in table.indexes} == {
        "IDX_file1_hash",
        "IDX_file2_hash",
        "IDX_unique_id",
        "IDX_userid",
        "idx_crewid_dhash",
        "idx_crewid_phash",
    }

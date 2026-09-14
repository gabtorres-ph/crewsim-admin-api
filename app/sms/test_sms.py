from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.common.exceptions import ResourceConflictError, ResourceNotFoundError
from app.sms.manager import SmsManager
from app.sms.models import Sms
from app.sms.resource_access import SmsResourceAccess
from app.sms.schemas import SmsCreate, SmsUpdate


def sms_values(**overrides):
    values = {
        "user_id": 1001,
        "imsi": "515020000000001",
        "sender": "CrewSim",
        "sms_text": "Welcome aboard.",
        "template": "welcome",
        "language": "en",
        "created_at": datetime.fromisoformat("2026-09-14T08:30:00"),
        "sent_at": None,
        "sent_result_code": None,
        "sent_result_text": None,
        "retry_counter": None,
    }
    values.update(overrides)
    return values


def sms_json(**overrides):
    values = sms_values(**overrides)
    for field in ("created_at", "sent_at"):
        if values[field] is not None:
            values[field] = values[field].isoformat()
    return values


def test_sms_resource_access_crud_and_pagination(db_session: Session) -> None:
    records = SmsResourceAccess(db_session)
    first = records.create(sms_values())
    second = records.create(sms_values(imsi="515020000000002"))
    third = records.create(sms_values(imsi="515020000000003"))

    assert records.get(first.id) is first
    assert records.list(offset=1, limit=1) == [second]
    assert records.list(offset=2, limit=10) == [third]

    records.update(first, {"sent_result_code": "OK", "retry_counter": 1})
    assert first.sent_result_code == "OK"
    assert first.retry_counter == 1

    records.delete(third)
    assert records.get(third.id) is None


def test_sms_manager_crud_nullable_update_and_commits(db_session: Session) -> None:
    manager = SmsManager(db_session)
    record = manager.create_sms(SmsCreate(**sms_values()))

    with Session(db_session.get_bind()) as other_session:
        assert other_session.get(Sms, record.id) is not None

    updated = manager.update_sms(
        record.id,
        SmsUpdate(
            template=None,
            sent_at=None,
            sent_result_code=None,
            sent_result_text=None,
            retry_counter=None,
        ),
    )
    assert updated.template is None
    assert updated.sent_at is None
    assert updated.sent_result_code is None
    assert updated.sent_result_text is None
    assert updated.retry_counter is None

    manager.delete_sms(record.id)
    with pytest.raises(ResourceNotFoundError, match=f"SMS '{record.id}' was not found"):
        manager.get_sms(record.id)


def test_sms_manager_rolls_back_database_conflicts(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = SmsManager(db_session)

    def create_invalid_sms(values) -> Sms:
        record = Sms()
        db_session.add(record)
        db_session.flush()
        return record

    monkeypatch.setattr(manager.sms, "create", create_invalid_sms)

    with pytest.raises(ResourceConflictError, match="SMS record conflicts"):
        manager.create_sms(SmsCreate(**sms_values()))

    assert manager.list_sms() == []


@pytest.mark.asyncio
async def test_sms_crud_pagination_and_response_shape(client) -> None:
    first_response = await client.post("/api/sms", json=sms_json())
    assert first_response.status_code == 201
    first = first_response.json()
    assert first == {"id": first["id"], **sms_json()}

    sent_at = datetime.fromisoformat("2026-09-14T08:31:00")
    second_response = await client.post(
        "/api/sms",
        json=sms_json(
            imsi="515020000000002",
            template=None,
            sent_at=sent_at,
            sent_result_code="OK",
            sent_result_text="Sent",
            retry_counter=0,
        ),
    )
    assert second_response.status_code == 201
    second = second_response.json()

    assert (await client.get(f"/api/sms/{first['id']}")).json() == first
    assert (await client.get("/api/sms?offset=1&limit=1")).json() == [second]

    update_response = await client.patch(
        f"/api/sms/{first['id']}",
        json={"sms_text": "Updated message", "sent_result_code": "QUEUED"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["sms_text"] == "Updated message"
    assert updated["sent_result_code"] == "QUEUED"
    assert updated["imsi"] == "515020000000001"

    assert (await client.delete(f"/api/sms/{first['id']}")).status_code == 204
    assert (await client.get(f"/api/sms/{first['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_sms_routes_validate_payloads_and_parameters(client) -> None:
    assert (await client.post("/api/sms", json={})).status_code == 422
    assert (await client.post("/api/sms", json=sms_json(imsi="  "))).status_code == 422
    assert (
        await client.post("/api/sms", json=sms_json(sender="x" * 101))
    ).status_code == 422
    assert (
        await client.post("/api/sms", json=sms_json(sms_text="x" * 3001))
    ).status_code == 422
    assert (
        await client.post("/api/sms", json=sms_json(language="eng"))
    ).status_code == 422
    assert (
        await client.post("/api/sms", json=sms_json(sent_result_code="x" * 51))
    ).status_code == 422
    assert (
        await client.post("/api/sms", json=sms_json(sent_result_text="x" * 151))
    ).status_code == 422

    record = (await client.post("/api/sms", json=sms_json())).json()
    assert (
        await client.patch(f"/api/sms/{record['id']}", json={"sms_text": None})
    ).status_code == 422
    nullable_response = await client.patch(
        f"/api/sms/{record['id']}", json={"sent_result_code": None}
    )
    assert nullable_response.status_code == 200
    assert nullable_response.json()["sent_result_code"] is None

    assert (await client.get("/api/sms/0")).status_code == 422
    assert (await client.get("/api/sms?offset=-1")).status_code == 422
    assert (await client.get("/api/sms?limit=0")).status_code == 422
    assert (await client.get("/api/sms?limit=101")).status_code == 422


def test_sms_model_preserves_database_columns_and_indexes() -> None:
    table = Sms.__table__

    assert Sms.user_id.property.columns[0].name == "userid"
    assert Sms.sms_text.property.columns[0].name == "smstext"
    assert Sms.created_at.property.columns[0].name == "createdate"
    assert Sms.sent_at.property.columns[0].name == "sentdate"
    assert Sms.sent_result_code.property.columns[0].name == "sentresultcode"
    assert Sms.sent_result_text.property.columns[0].name == "sentresulttext"
    assert Sms.retry_counter.property.columns[0].name == "retrycounter"
    assert {index.name for index in table.indexes} == {
        "userid_idx",
        "imsi_idx",
        "createdate_idx",
        "sentresultcode_idx",
        "sentdate_idx",
    }

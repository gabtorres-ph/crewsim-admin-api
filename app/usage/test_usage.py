from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.common.exceptions import ResourceConflictError, ResourceNotFoundError
from app.usage.manager import UsageManager
from app.usage.models import Usage
from app.usage.resource_access import UsageResourceAccess
from app.usage.schemas import UsageCreate, UsageUpdate


def usage_values(**overrides):
    values = {
        "usage_date_utc": datetime.fromisoformat("2026-09-07T08:30:00"),
        "session_id": "session-1",
        "mcc": 515,
        "mnc": 2,
        "total_qty": 1024,
        "usage_type_id": 1,
        "usage_type": "data",
        "dest_phone_number": None,
        "subs_reseller_name": "CrewSim",
        "custo_account_name": "Customer",
        "subs_account_name": "Subscriber",
        "subscriber_id": 1001,
        "imsi": "515020000000001",
        "iccid": "8901000000000000001",
        "subs_phone_number": "+639170000001",
        "prepaid_package_ids": "10,11",
        "prepaid_package_qtys": "1,2",
        "toll_free": "false",
        "custo_account_id": 2001,
        "custo_charge": Decimal("1.234567890123456"),
        "subs_account_id": 3001,
        "subs_charge": Decimal("2.345678901234567"),
        "apn": "internet",
        "rat": 4,
        "imei": "350000000000001",
        "down_bitrate": 5000000000,
        "up_bitrate": 1000000000,
        "filename": "usage-20260907.csv",
    }
    values.update(overrides)
    return values


def usage_json(**overrides):
    values = usage_values(**overrides)
    values["usage_date_utc"] = values["usage_date_utc"].isoformat()
    for field in ("custo_charge", "subs_charge"):
        if values[field] is not None:
            values[field] = str(values[field])
    return values


def test_usage_resource_access_crud_and_pagination(db_session: Session) -> None:
    records = UsageResourceAccess(db_session)
    first = records.create(usage_values())
    second = records.create(usage_values(session_id="session-2"))
    third = records.create(usage_values(session_id="session-3"))

    assert records.get(first.id) is first
    assert records.list(offset=1, limit=1) == [second]
    assert records.list(offset=2, limit=10) == [third]

    records.update(first, {"total_qty": 2048, "dest_phone_number": "+639170000002"})
    assert first.total_qty == 2048
    assert first.dest_phone_number == "+639170000002"

    records.delete(third)
    assert records.get(third.id) is None


def test_usage_manager_crud_nullable_update_and_commits(db_session: Session) -> None:
    manager = UsageManager(db_session)
    record = manager.create_usage(UsageCreate(**usage_values()))

    with Session(db_session.get_bind()) as other_session:
        assert other_session.get(Usage, record.id) is not None

    updated = manager.update_usage(
        record.id,
        UsageUpdate(
            dest_phone_number=None,
            custo_account_id=None,
            custo_charge=None,
            subs_account_id=None,
            subs_charge=None,
        ),
    )
    assert updated.dest_phone_number is None
    assert updated.custo_account_id is None
    assert updated.custo_charge is None
    assert updated.subs_account_id is None
    assert updated.subs_charge is None

    manager.delete_usage(record.id)
    with pytest.raises(ResourceNotFoundError, match=f"Usage '{record.id}' was not found"):
        manager.get_usage(record.id)


def test_usage_manager_rolls_back_database_conflicts(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = UsageManager(db_session)

    def create_invalid_usage(values) -> Usage:
        record = Usage()
        db_session.add(record)
        db_session.flush()
        return record

    monkeypatch.setattr(manager.usage, "create", create_invalid_usage)

    with pytest.raises(ResourceConflictError, match="usage record conflicts"):
        manager.create_usage(UsageCreate(**usage_values()))

    assert manager.list_usage() == []


@pytest.mark.asyncio
async def test_usage_crud_pagination_and_response_shape(client) -> None:
    first_response = await client.post("/api/usage", json=usage_json())
    assert first_response.status_code == 201
    first = first_response.json()
    assert first == {"id": first["id"], **usage_json()}

    second_response = await client.post(
        "/api/usage",
        json=usage_json(
            session_id="session-2",
            dest_phone_number="+639170000002",
            custo_account_id=None,
            custo_charge=None,
            subs_account_id=None,
            subs_charge=None,
        ),
    )
    assert second_response.status_code == 201
    second = second_response.json()

    assert (await client.get(f"/api/usage/{first['id']}")).json() == first
    assert (await client.get("/api/usage?offset=1&limit=1")).json() == [second]

    update_response = await client.patch(
        f"/api/usage/{first['id']}",
        json={"total_qty": 4096, "dest_phone_number": None, "custo_charge": None},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["total_qty"] == 4096
    assert updated["dest_phone_number"] is None
    assert updated["custo_charge"] is None
    assert updated["session_id"] == "session-1"

    assert (await client.delete(f"/api/usage/{first['id']}")).status_code == 204
    assert (await client.get(f"/api/usage/{first['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_usage_routes_validate_payloads_and_parameters(client) -> None:
    assert (await client.post("/api/usage", json={})).status_code == 422
    assert (
        await client.post("/api/usage", json=usage_json(session_id="  "))
    ).status_code == 422
    assert (
        await client.post("/api/usage", json=usage_json(filename="x" * 101))
    ).status_code == 422
    assert (
        await client.post("/api/usage", json=usage_json(toll_free="x" * 11))
    ).status_code == 422
    assert (
        await client.post(
            "/api/usage", json=usage_json(custo_charge="123456.123456789012345")
        )
    ).status_code == 422

    record = (await client.post("/api/usage", json=usage_json())).json()
    assert (
        await client.patch(f"/api/usage/{record['id']}", json={"session_id": None})
    ).status_code == 422
    nullable_response = await client.patch(
        f"/api/usage/{record['id']}", json={"custo_account_id": None}
    )
    assert nullable_response.status_code == 200
    assert nullable_response.json()["custo_account_id"] is None

    assert (await client.get("/api/usage/0")).status_code == 422
    assert (await client.get("/api/usage?offset=-1")).status_code == 422
    assert (await client.get("/api/usage?limit=0")).status_code == 422
    assert (await client.get("/api/usage?limit=101")).status_code == 422


def test_usage_model_preserves_database_column_and_indexes() -> None:
    table = Usage.__table__

    assert Usage.custo_account_id.property.columns[0].name == "CUSTO_ACCOUNT_ID"
    assert {index.name for index in table.indexes} == {
        "idx_usage_date_utc",
        "idx_imsi",
        "idx_iccid",
        "idx_imsi_usage_dt",
    }

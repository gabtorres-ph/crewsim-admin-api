from datetime import datetime

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.common.exceptions import ResourceConflictError, ResourceNotFoundError
from app.sim_notifications.manager import SimNotificationManager
from app.sim_notifications.models import (
    SimNotification,
    SimNotificationProvider,
    SimNotificationType,
)
from app.sim_notifications.resource_access import SimNotificationResourceAccess
from app.sim_notifications.schemas import SimNotificationCreate


def sim_notification_values(**overrides):
    values = {
        "typ": SimNotificationType.LOCATION,
        "imsi": "260010180730303",
        "provider": SimNotificationProvider.TELCOVISION,
        "payload": {"mcc": "260", "mnc": "01", "country": "PL"},
    }
    values.update(overrides)
    return values


def test_sim_notification_resource_access_orders_by_id_desc_and_filters(
    db_session: Session,
) -> None:
    notifications = SimNotificationResourceAccess(db_session)
    first = notifications.create(sim_notification_values())
    second = notifications.create(sim_notification_values(typ=SimNotificationType.ES2))
    third = notifications.create(
        sim_notification_values(typ=SimNotificationType.PACKAGE, imsi="260010180730304")
    )

    assert first.createdate is not None
    assert notifications.list() == [third, second, first]
    assert notifications.list(offset=1, limit=1) == [second]
    assert notifications.list(typ=SimNotificationType.ES2) == [second]
    assert notifications.list(imsi="260010180730303") == [second, first]

    notifications.delete(third)
    assert notifications.get(third.id) is None


def test_sim_notification_manager_crud_and_commits(db_session: Session) -> None:
    manager = SimNotificationManager(db_session)
    createdate = datetime.fromisoformat("2026-10-12T08:30:00")
    notification = manager.create_notification(
        SimNotificationCreate(**sim_notification_values(createdate=createdate))
    )
    assert notification.createdate == createdate
    assert notification.payload == {"mcc": "260", "mnc": "01", "country": "PL"}

    with Session(db_session.get_bind()) as other_session:
        assert other_session.get(SimNotification, notification.id) is not None

    manager.delete_notification(notification.id)
    with pytest.raises(
        ResourceNotFoundError,
        match=f"SIM notification '{notification.id}' was not found",
    ):
        manager.get_notification(notification.id)


def test_sim_notification_manager_rolls_back_database_conflicts(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = SimNotificationManager(db_session)

    def create_invalid_notification(values) -> SimNotification:
        notification = SimNotification()
        db_session.add(notification)
        db_session.flush()
        return notification

    monkeypatch.setattr(manager.notifications, "create", create_invalid_notification)

    with pytest.raises(ResourceConflictError, match="SIM notification conflicts"):
        manager.create_notification(SimNotificationCreate(**sim_notification_values()))

    assert manager.list_notifications() == []


def test_sim_notification_schemas_validate_payloads() -> None:
    with pytest.raises(ValidationError):
        SimNotificationCreate(**sim_notification_values(typ="sms"))

    with pytest.raises(ValidationError):
        SimNotificationCreate(**sim_notification_values(imsi="2600101807303031"))

    with pytest.raises(ValidationError):
        SimNotificationCreate(**sim_notification_values(imsi="26001abc"))

    with pytest.raises(ValidationError):
        SimNotificationCreate(**sim_notification_values(provider="unknown"))


@pytest.mark.asyncio
async def test_sim_notification_routes(client: AsyncClient) -> None:
    sim_notification = {
        "typ": "ES2",
        "imsi": "260010180730303",
        "provider": "telcovision",
        "payload": {"event": "download"},
    }
    response = await client.post("/api/sim/notifications", json=sim_notification)
    assert response.status_code == 405

    # Records are only created through provider webhooks.
    response = await client.post(
        "/api/webhooks/telcovision/es2", json={"imsi": "260010180730303", "status": "Enable"}
    )
    assert response.status_code == 200

    response = await client.get("/api/sim/notifications")
    [created] = response.json()
    assert created["typ"] == "ES2"
    assert created["provider"] == "telcovision"
    assert created["createdate"]

    response = await client.get("/api/sim/notifications", params={"typ": "ES2"})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [created["id"]]

    response = await client.get("/api/sim/notifications", params={"typ": "location"})
    assert response.json() == []

    response = await client.patch(
        f"/api/sim/notifications/{created['id']}", json={"payload": {"state": "attached"}}
    )
    assert response.status_code == 405

    response = await client.delete(f"/api/sim/notifications/{created['id']}")
    assert response.status_code == 204

    response = await client.get(f"/api/sim/notifications/{created['id']}")
    assert response.status_code == 404


def test_sim_notification_model_preserves_database_indexes() -> None:
    table = SimNotification.__table__

    assert {index.name for index in table.indexes} == {
        "idx_sim_notification_typ",
        "idx_sim_notification_imsi",
        "idx_sim_notification_createdate",
    }

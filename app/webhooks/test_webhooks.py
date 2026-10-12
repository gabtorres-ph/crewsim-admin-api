import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.telcovision.test_telcovision import (
    ES2_PAYLOAD,
    LOCATION_PAYLOAD,
    PACKAGE_PAYLOAD,
)
from app.sim_notifications.models import SimNotification


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "payload", "typ", "imsi"),
    [
        ("es2", ES2_PAYLOAD, "ES2", "123456789123456"),
        ("location", LOCATION_PAYLOAD, "location", "260010180730303"),
        ("package", PACKAGE_PAYLOAD, "package", "123456789"),
    ],
)
async def test_telcovision_webhook_stores_sim_notification(
    client: AsyncClient,
    db_session: Session,
    path: str,
    payload: dict,
    typ: str,
    imsi: str,
) -> None:
    response = await client.post(f"/api/webhooks/telcovision/{path}", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    notification = db_session.scalars(select(SimNotification)).one()
    assert notification.typ == typ
    assert notification.imsi == imsi
    assert notification.provider == "telcovision"
    assert notification.payload == payload
    assert notification.createdate is not None


@pytest.mark.asyncio
async def test_telcovision_webhook_rejects_payload_without_imsi(
    client: AsyncClient, db_session: Session
) -> None:
    payload = {key: value for key, value in ES2_PAYLOAD.items() if key != "imsi"}

    response = await client.post("/api/webhooks/telcovision/es2", json=payload)

    assert response.status_code == 422
    assert db_session.scalars(select(SimNotification)).all() == []

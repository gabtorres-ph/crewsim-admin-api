from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.integrations.telcovision.mapper import (
    es2_to_sim_notification,
    location_to_sim_notification,
    package_to_sim_notification,
)
from app.integrations.telcovision.schemas import (
    TelcovisionEs2Event,
    TelcovisionLocationEvent,
    TelcovisionPackageEvent,
)
from app.sim_notifications.manager import SimNotificationManager
from app.webhooks.schemas import WebhookAck

# TODO: add provider request verification as a router dependency once Telcovision supplies it.
router = APIRouter(prefix="/telcovision", tags=["webhooks"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("/es2", response_model=WebhookAck)
def receive_es2(event: TelcovisionEs2Event, db: DatabaseSession) -> WebhookAck:
    SimNotificationManager(db).create_notification(es2_to_sim_notification(event))
    return WebhookAck()


@router.post("/location", response_model=WebhookAck)
def receive_location(event: TelcovisionLocationEvent, db: DatabaseSession) -> WebhookAck:
    SimNotificationManager(db).create_notification(location_to_sim_notification(event))
    return WebhookAck()


@router.post("/package", response_model=WebhookAck)
def receive_package(event: TelcovisionPackageEvent, db: DatabaseSession) -> WebhookAck:
    SimNotificationManager(db).create_notification(package_to_sim_notification(event))
    return WebhookAck()

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.sim_notifications.manager import SimNotificationManager
from app.sim_notifications.models import SimNotificationType
from app.sim_notifications.schemas import (
    SimNotificationCreate,
    SimNotificationRead,
    SimNotificationUpdate,
)

router = APIRouter(prefix="/sim/notifications", tags=["sim notifications"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=SimNotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(data: SimNotificationCreate, db: DatabaseSession) -> SimNotificationRead:
    return SimNotificationManager(db).create_notification(data)


@router.get("", response_model=list[SimNotificationRead])
def list_notifications(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    typ: SimNotificationType | None = None,
    imsi: Annotated[str | None, Query(pattern=r"^\d{5,15}$")] = None,
) -> list[SimNotificationRead]:
    return SimNotificationManager(db).list_notifications(
        offset=offset, limit=limit, typ=typ, imsi=imsi
    )


@router.get("/{notification_id}", response_model=SimNotificationRead)
def get_notification(
    notification_id: Annotated[int, Path(gt=0)], db: DatabaseSession
) -> SimNotificationRead:
    return SimNotificationManager(db).get_notification(notification_id)


@router.patch("/{notification_id}", response_model=SimNotificationRead)
def update_notification(
    notification_id: Annotated[int, Path(gt=0)],
    data: SimNotificationUpdate,
    db: DatabaseSession,
) -> SimNotificationRead:
    return SimNotificationManager(db).update_notification(notification_id, data)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: Annotated[int, Path(gt=0)], db: DatabaseSession
) -> Response:
    SimNotificationManager(db).delete_notification(notification_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.stripe.manager import StripeManager
from app.stripe.schemas import (
    StripeNotificationCreate,
    StripeNotificationRead,
    StripeNotificationUpdate,
)

router = APIRouter(prefix="/stripe/notifications", tags=["stripe"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=StripeNotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(
    data: StripeNotificationCreate, db: DatabaseSession
) -> StripeNotificationRead:
    return StripeManager(db).create_notification(data)


@router.get("", response_model=list[StripeNotificationRead])
def list_notifications(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[StripeNotificationRead]:
    return StripeManager(db).list_notifications(offset=offset, limit=limit)


@router.get("/{notification_id}", response_model=StripeNotificationRead)
def get_notification(
    notification_id: Annotated[int, Path(gt=0)], db: DatabaseSession
) -> StripeNotificationRead:
    return StripeManager(db).get_notification(notification_id)


@router.patch("/{notification_id}", response_model=StripeNotificationRead)
def update_notification(
    notification_id: Annotated[int, Path(gt=0)],
    data: StripeNotificationUpdate,
    db: DatabaseSession,
) -> StripeNotificationRead:
    return StripeManager(db).update_notification(notification_id, data)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: Annotated[int, Path(gt=0)], db: DatabaseSession
) -> Response:
    StripeManager(db).delete_notification(notification_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

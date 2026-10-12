from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from app.sim_notifications.models import SimNotificationProvider, SimNotificationType

Imsi = Annotated[str, Field(pattern=r"^\d{5,15}$")]


class SimNotificationBase(BaseModel):
    typ: SimNotificationType
    imsi: Imsi
    provider: SimNotificationProvider
    payload: dict[str, Any]

    model_config = ConfigDict(str_strip_whitespace=True)


class SimNotificationCreate(SimNotificationBase):
    createdate: datetime | None = None


class SimNotificationRead(SimNotificationBase):
    id: int
    createdate: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

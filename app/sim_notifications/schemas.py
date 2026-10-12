from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.sim_notifications.models import SimNotificationType

Imsi = Annotated[str, Field(pattern=r"^\d{5,15}$")]


class SimNotificationBase(BaseModel):
    typ: SimNotificationType
    imsi: Imsi
    payload: dict[str, Any]

    model_config = ConfigDict(str_strip_whitespace=True)


class SimNotificationCreate(SimNotificationBase):
    createdate: datetime | None = None


class SimNotificationUpdate(BaseModel):
    typ: SimNotificationType | None = None
    imsi: Imsi | None = None
    payload: dict[str, Any] | None = None
    createdate: datetime | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("typ", "imsi", "payload", "createdate")
    @classmethod
    def reject_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class SimNotificationRead(SimNotificationBase):
    id: int
    createdate: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

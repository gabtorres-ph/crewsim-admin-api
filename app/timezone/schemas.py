from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

TimezoneName = Annotated[str, Field(min_length=1, max_length=255)]


class TimezoneCreate(BaseModel):
    name: TimezoneName

    model_config = ConfigDict(str_strip_whitespace=True)


class TimezoneUpdate(BaseModel):
    name: TimezoneName | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("name")
    @classmethod
    def reject_null_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class TimezoneRead(BaseModel):
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

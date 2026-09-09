from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

WhitelistEmail = Annotated[str, Field(min_length=1, max_length=255)]
WhitelistStatus = Annotated[str, Field(min_length=1, max_length=20)]


class EmailWhitelistCreate(BaseModel):
    email: WhitelistEmail
    status: WhitelistStatus

    model_config = ConfigDict(str_strip_whitespace=True)


class EmailWhitelistUpdate(BaseModel):
    email: WhitelistEmail | None = None
    status: WhitelistStatus | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("email", "status")
    @classmethod
    def reject_null_fields(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class EmailWhitelistRead(BaseModel):
    id: int
    email: str
    createdate: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)

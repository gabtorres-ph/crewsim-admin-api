from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

NonEmptyString = Annotated[str, Field(min_length=1, max_length=255)]
ReferralCode = Annotated[str, Field(min_length=1, max_length=8)]


class UserBase(BaseModel):
    email: NonEmptyString
    language: NonEmptyString
    currency: NonEmptyString
    timezone: NonEmptyString
    firstname: NonEmptyString | None = None
    lastname: NonEmptyString | None = None
    airline: NonEmptyString | None = None
    position: NonEmptyString | None = None
    referralcode: ReferralCode | None = None
    referredby: int | None = Field(default=None, gt=0)
    stripeid: NonEmptyString | None = None
    logtoid: NonEmptyString | None = None
    createdate: datetime | None = None
    newsletter: bool | None = None
    smsnotification: bool | None = None
    rateus: datetime | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    email: NonEmptyString | None = None
    language: NonEmptyString | None = None
    currency: NonEmptyString | None = None
    timezone: NonEmptyString | None = None
    firstname: NonEmptyString | None = None
    lastname: NonEmptyString | None = None
    airline: NonEmptyString | None = None
    position: NonEmptyString | None = None
    referralcode: ReferralCode | None = None
    referredby: int | None = Field(default=None, gt=0)
    stripeid: NonEmptyString | None = None
    logtoid: NonEmptyString | None = None
    createdate: datetime | None = None
    newsletter: bool | None = None
    smsnotification: bool | None = None
    rateus: datetime | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator(
        "email", "language", "currency", "timezone", "firstname", "lastname", "airline",
        "position", "referralcode", "referredby", "stripeid", "logtoid", "createdate",
        "newsletter", "smsnotification", "rateus",
    )
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class UserRead(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

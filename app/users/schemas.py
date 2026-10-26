from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.currencies.schemas import CurrencyCode
from app.language.schemas import Iso1
from app.timezone.schemas import TimezoneName

NonEmptyString = Annotated[str, Field(min_length=1, max_length=255)]
ReferralCode = Annotated[str, Field(min_length=1, max_length=8)]


class UserBase(BaseModel):
    email: NonEmptyString
    lang_iso1: Iso1
    currency_code: CurrencyCode
    timezone: TimezoneName
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
    lang_iso1: Iso1 | None = None
    currency_code: CurrencyCode | None = None
    timezone: TimezoneName | None = None
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
        "email",
        "lang_iso1",
        "currency_code",
        "timezone",
        "firstname",
        "lastname",
        "airline",
        "position",
        "referralcode",
        "referredby",
        "stripeid",
        "logtoid",
        "createdate",
        "newsletter",
        "smsnotification",
        "rateus",
    )
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class UserRead(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

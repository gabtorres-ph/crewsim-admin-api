from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

NonEmptyString = Annotated[str, Field(min_length=1, max_length=255)]


class UserBase(BaseModel):
    email: NonEmptyString
    language: NonEmptyString
    sex: NonEmptyString
    currency: NonEmptyString
    timezone: NonEmptyString

    model_config = ConfigDict(str_strip_whitespace=True)


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    email: NonEmptyString | None = None
    language: NonEmptyString | None = None
    sex: NonEmptyString | None = None
    currency: NonEmptyString | None = None
    timezone: NonEmptyString | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("email", "language", "currency", "timezone")
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class UserRead(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

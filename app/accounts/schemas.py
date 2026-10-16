from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

AccountName = Annotated[str, Field(min_length=1, max_length=255)]


class AccountCreate(BaseModel):
    name: AccountName
    balance: float

    model_config = ConfigDict(str_strip_whitespace=True)


class AccountUpdate(BaseModel):
    name: AccountName | None = None
    balance: float | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("name", "balance")
    @classmethod
    def reject_null(cls, value: str | float | None) -> str | float:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class AccountRead(BaseModel):
    id: int
    name: str
    balance: float
    reseller_id: int | None = None
    package_only: bool | None = None
    steering_list_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class AccountSnapshot(BaseModel):
    id: int = Field(gt=0)
    reseller_id: int = Field(gt=0)
    name: AccountName
    balance: float = Field(allow_inf_nan=False)
    package_only: bool
    steering_list_id: int | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class AccountRefreshResult(BaseModel):
    fetched: int = Field(ge=0)
    created: int = Field(ge=0)
    updated: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    deleted: int = Field(ge=0)

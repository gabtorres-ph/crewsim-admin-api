from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

IMSIString = Annotated[str, Field(min_length=1, max_length=255)]
TokenString = Annotated[str, Field(min_length=1, max_length=8)]


class ESIMCreate(BaseModel):
    user_id: int | None = Field(default=None, gt=0)
    account_id: int = Field(gt=0)
    imsi: IMSIString
    name: IMSIString | None = None
    isesim: bool | None = None
    createdate: datetime | None = None
    token: TokenString | None = None
    networkstatus: IMSIString | None = None
    balance: float | None = None
    use_account_for_charging: bool = False
    smdpserver: IMSIString | None = None
    activationcode: IMSIString | None = None
    imei: IMSIString | None = None
    imei_device: IMSIString | None = None
    allow_data: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class ESIMUpdate(BaseModel):
    user_id: int | None = Field(default=None, gt=0)
    account_id: int | None = Field(default=None, gt=0)
    imsi: IMSIString | None = None
    name: IMSIString | None = None
    isesim: bool | None = None
    createdate: datetime | None = None
    token: TokenString | None = None
    networkstatus: IMSIString | None = None
    balance: float | None = None
    use_account_for_charging: bool | None = None
    smdpserver: IMSIString | None = None
    activationcode: IMSIString | None = None
    imei: IMSIString | None = None
    imei_device: IMSIString | None = None
    allow_data: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator(
        "user_id",
        "account_id",
        "imsi",
        "name",
        "isesim",
        "createdate",
        "token",
        "networkstatus",
        "balance",
        "use_account_for_charging",
        "smdpserver",
        "activationcode",
        "imei",
        "imei_device",
        "allow_data",
    )
    @classmethod
    def reject_null(cls, value: int | str | None) -> int | str:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class ESIMRead(BaseModel):
    id: int
    user_id: int | None = Field(validation_alias="userid")
    account_id: int = Field(validation_alias="accountid")
    imsi: str
    name: str | None
    isesim: bool | None
    createdate: datetime | None
    token: str | None
    networkstatus: str | None
    balance: float | None
    use_account_for_charging: bool
    smdpserver: str | None
    activationcode: str | None
    imei: str | None
    imei_device: str | None
    allow_data: bool | None

    model_config = ConfigDict(from_attributes=True)

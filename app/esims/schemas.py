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
    mobileplanid: int | None = None
    activationdate: datetime | None = None
    lastusagedate: datetime | None = None
    subscriber_status: IMSIString | None = None
    lastnetworkdate: datetime | None = None
    lastmcc: IMSIString | None = None
    lastmnc: IMSIString | None = None
    lastcellid: int | None = None
    lastlac: int | None = None
    lastrat: IMSIString | None = None

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
    mobileplanid: int | None = None
    activationdate: datetime | None = None
    lastusagedate: datetime | None = None
    subscriber_status: IMSIString | None = None
    lastnetworkdate: datetime | None = None
    lastmcc: IMSIString | None = None
    lastmnc: IMSIString | None = None
    lastcellid: int | None = None
    lastlac: int | None = None
    lastrat: IMSIString | None = None

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
        "mobileplanid",
        "activationdate",
        "lastusagedate",
        "subscriber_status",
        "lastnetworkdate",
        "lastmcc",
        "lastmnc",
        "lastcellid",
        "lastlac",
        "lastrat",
    )
    @classmethod
    def reject_null(cls, value: int | str | None) -> int | str:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class ESIMRead(BaseModel):
    id: int
    user_id: int | None = Field(validation_alias="userid")
    account_id: int | None = Field(validation_alias="accountid")
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
    mobileplanid: int | None
    activationdate: datetime | None
    lastusagedate: datetime | None
    subscriber_status: str | None
    lastnetworkdate: datetime | None
    lastmcc: str | None
    lastmnc: str | None
    lastcellid: int | None
    lastlac: int | None
    lastrat: str | None

    model_config = ConfigDict(from_attributes=True)


class ESIMSnapshot(BaseModel):
    imsi: IMSIString = Field(pattern=r"^[0-9]{5,15}$")
    account_id: int = Field(gt=0, strict=True)
    isesim: bool = Field(strict=True)
    balance: float | None = Field(default=None, allow_inf_nan=False)
    use_account_for_charging: bool = Field(strict=True)
    smdpserver: IMSIString | None = None
    activationcode: IMSIString | None = None
    allow_data: bool = Field(strict=True)
    mobileplanid: int | None = Field(default=None, gt=0, strict=True)
    activationdate: datetime | None = None
    lastusagedate: datetime | None = None
    subscriber_status: IMSIString | None = None
    lastnetworkdate: datetime | None = None
    lastmcc: IMSIString | None = None
    lastmnc: IMSIString | None = None
    lastcellid: int | None = None
    lastlac: int | None = None
    imei: IMSIString | None = None
    imei_device: IMSIString | None = None
    lastrat: IMSIString | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class ESIMSingleSnapshot(BaseModel):
    imsi: IMSIString = Field(pattern=r"^[0-9]{5,15}$")
    account_id: int | None = Field(default=None, gt=0, strict=True)
    balance: float | None = Field(default=None, allow_inf_nan=False)
    use_account_for_charging: bool | None = Field(default=None, strict=True)
    allow_data: bool | None = Field(default=None, strict=True)
    mobileplanid: int | None = Field(default=None, gt=0, strict=True)
    activationdate: datetime | None = None
    lastusagedate: datetime | None = None
    subscriber_status: IMSIString | None = None
    lastnetworkdate: datetime | None = None
    lastmcc: IMSIString | None = None
    lastmnc: IMSIString | None = None
    lastcellid: int | None = None
    lastlac: int | None = None
    imei: IMSIString | None = None
    imei_device: IMSIString | None = None
    lastrat: IMSIString | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("use_account_for_charging")
    @classmethod
    def reject_null_charging(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class ESIMRefreshResult(BaseModel):
    # this schema will be reused for the listSubscribers and
    # getSingleSubcriber call to telcovision
    id: int
    imsi: str
    account_id: int | None = Field(default=None, validation_alias="accountid")
    networkstatus: str | None = None
    isesim: bool | None = None
    balance: float | None = None
    use_account_for_charging: bool | None = None
    smdpserver: str | None = None
    activationcode: str | None = None
    allow_data: bool | None = None
    mobileplanid: int | None = None
    activationdate: datetime | None = None
    lastusagedate: datetime | None = None
    subscriber_status: str | None = None
    lastnetworkdate: datetime | None = None
    lastmcc: str | None = None
    lastmnc: str | None = None
    lastcellid: int | None = None
    lastlac: int | None = None
    imei: str | None = None
    imei_device: str | None = None
    lastrat: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ESIMMoveRequest(BaseModel):
    source_account_id: int = Field(gt=0)
    destination_account_id: int = Field(gt=0)
    imsis: list[Annotated[IMSIString, Field(pattern=r"^[0-9]{5,15}$")]] = Field(min_length=1)

    @field_validator("imsis")
    @classmethod
    def reject_duplicate_imsis(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("IMSIs must be unique")
        return value


class ESIMMoveResult(BaseModel):
    imsi: str
    account_id: int

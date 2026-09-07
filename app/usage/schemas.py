from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

UsageString = Annotated[str, Field(min_length=1, max_length=100)]
TollFreeString = Annotated[str, Field(min_length=1, max_length=10)]
Charge = Annotated[Decimal, Field(max_digits=20, decimal_places=15)]


class UsageBase(BaseModel):
    usage_date_utc: datetime
    session_id: UsageString
    mcc: int
    mnc: int
    total_qty: int
    usage_type_id: int
    usage_type: UsageString
    dest_phone_number: UsageString | None = None
    subs_reseller_name: UsageString
    custo_account_name: UsageString
    subs_account_name: UsageString
    subscriber_id: int
    imsi: UsageString
    iccid: UsageString
    subs_phone_number: UsageString
    prepaid_package_ids: UsageString
    prepaid_package_qtys: UsageString
    toll_free: TollFreeString
    custo_account_id: int | None = None
    custo_charge: Charge | None = None
    subs_account_id: int | None = None
    subs_charge: Charge | None = None
    apn: UsageString
    rat: int
    imei: UsageString
    down_bitrate: int
    up_bitrate: int
    filename: UsageString

    model_config = ConfigDict(str_strip_whitespace=True)


class UsageCreate(UsageBase):
    pass


class UsageUpdate(BaseModel):
    usage_date_utc: datetime | None = None
    session_id: UsageString | None = None
    mcc: int | None = None
    mnc: int | None = None
    total_qty: int | None = None
    usage_type_id: int | None = None
    usage_type: UsageString | None = None
    dest_phone_number: UsageString | None = None
    subs_reseller_name: UsageString | None = None
    custo_account_name: UsageString | None = None
    subs_account_name: UsageString | None = None
    subscriber_id: int | None = None
    imsi: UsageString | None = None
    iccid: UsageString | None = None
    subs_phone_number: UsageString | None = None
    prepaid_package_ids: UsageString | None = None
    prepaid_package_qtys: UsageString | None = None
    toll_free: TollFreeString | None = None
    custo_account_id: int | None = None
    custo_charge: Charge | None = None
    subs_account_id: int | None = None
    subs_charge: Charge | None = None
    apn: UsageString | None = None
    rat: int | None = None
    imei: UsageString | None = None
    down_bitrate: int | None = None
    up_bitrate: int | None = None
    filename: UsageString | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator(
        "usage_date_utc",
        "session_id",
        "mcc",
        "mnc",
        "total_qty",
        "usage_type_id",
        "usage_type",
        "subs_reseller_name",
        "custo_account_name",
        "subs_account_name",
        "subscriber_id",
        "imsi",
        "iccid",
        "subs_phone_number",
        "prepaid_package_ids",
        "prepaid_package_qtys",
        "toll_free",
        "apn",
        "rat",
        "imei",
        "down_bitrate",
        "up_bitrate",
        "filename",
    )
    @classmethod
    def reject_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class UsageRead(UsageBase):
    id: int

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

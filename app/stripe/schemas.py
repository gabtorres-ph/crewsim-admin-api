from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

StripeString = Annotated[str, Field(min_length=1, max_length=100)]
StripeAmount = Annotated[Decimal, Field(max_digits=10, decimal_places=2)]


class StripeNotificationBase(BaseModel):
    eventid: StripeString
    invoiceid: StripeString
    customerid: StripeString
    taxrate: StripeAmount | None = None
    taxcountry: StripeString | None = None
    amount_net: StripeAmount
    amount_tax: StripeAmount
    amount_gross: StripeAmount
    currency: StripeString
    sku: StripeString
    userid: int
    state: StripeString | None = None
    createdate: datetime
    imsi: StripeString | None = None
    amount_credit: StripeAmount | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class StripeNotificationCreate(StripeNotificationBase):
    pass


class StripeNotificationUpdate(BaseModel):
    eventid: StripeString | None = None
    invoiceid: StripeString | None = None
    customerid: StripeString | None = None
    taxrate: StripeAmount | None = None
    taxcountry: StripeString | None = None
    amount_net: StripeAmount | None = None
    amount_tax: StripeAmount | None = None
    amount_gross: StripeAmount | None = None
    currency: StripeString | None = None
    sku: StripeString | None = None
    userid: int | None = None
    state: StripeString | None = None
    createdate: datetime | None = None
    imsi: StripeString | None = None
    amount_credit: StripeAmount | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator(
        "eventid",
        "invoiceid",
        "customerid",
        "amount_net",
        "amount_tax",
        "amount_gross",
        "currency",
        "sku",
        "userid",
        "createdate",
    )
    @classmethod
    def reject_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class StripeNotificationRead(StripeNotificationBase):
    id: int

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

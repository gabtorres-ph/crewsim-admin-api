from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

SmsString = Annotated[str, Field(min_length=1, max_length=100)]
SmsText = Annotated[str, Field(min_length=1, max_length=3000)]
LanguageCode = Annotated[str, Field(min_length=2, max_length=2)]
ResultCode = Annotated[str, Field(min_length=1, max_length=50)]
ResultText = Annotated[str, Field(min_length=1, max_length=150)]


class SmsBase(BaseModel):
    user_id: int
    imsi: SmsString
    sender: SmsString
    sms_text: SmsText
    template: SmsString | None = None
    language: LanguageCode
    created_at: datetime
    sent_at: datetime | None = None
    sent_result_code: ResultCode | None = None
    sent_result_text: ResultText | None = None
    retry_counter: int | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class SmsCreate(SmsBase):
    pass


class SmsUpdate(BaseModel):
    user_id: int | None = None
    imsi: SmsString | None = None
    sender: SmsString | None = None
    sms_text: SmsText | None = None
    template: SmsString | None = None
    language: LanguageCode | None = None
    created_at: datetime | None = None
    sent_at: datetime | None = None
    sent_result_code: ResultCode | None = None
    sent_result_text: ResultText | None = None
    retry_counter: int | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator(
        "user_id",
        "imsi",
        "sender",
        "sms_text",
        "language",
        "created_at",
    )
    @classmethod
    def reject_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class SmsRead(SmsBase):
    id: int

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

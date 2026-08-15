from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

IMSIString = Annotated[str, Field(min_length=1, max_length=255)]


class ESIMCreate(BaseModel):
    user_id: int = Field(gt=0)
    imsi: IMSIString

    model_config = ConfigDict(str_strip_whitespace=True)


class ESIMUpdate(BaseModel):
    user_id: int | None = Field(default=None, gt=0)
    imsi: IMSIString | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("user_id", "imsi")
    @classmethod
    def reject_null(cls, value: int | str | None) -> int | str:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class ESIMRead(BaseModel):
    id: int
    user_id: int = Field(validation_alias="userid")
    imsi: str

    model_config = ConfigDict(from_attributes=True)

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

UniqueID = Annotated[str, Field(min_length=1, max_length=50)]
FileName = Annotated[str, Field(min_length=1, max_length=100)]
PersonName = Annotated[str, Field(min_length=1, max_length=150)]
FileHash = Annotated[str, Field(min_length=1, max_length=64)]
Description = Annotated[str, Field(min_length=1, max_length=255)]
PerceptualHash = Annotated[str, Field(min_length=1, max_length=32)]
Confidence = Annotated[Decimal, Field(max_digits=10, decimal_places=2)]


class CrewBase(BaseModel):
    unique_id: UniqueID
    file1: FileName | None = None
    file2: FileName | None = None
    firstname: PersonName | None = None
    lastname: PersonName | None = None
    airline: PersonName | None = None
    iscrewid: bool
    createdate: datetime
    user_id: int | None = Field(default=None, gt=0)
    file1_hash: FileHash | None = None
    file2_hash: FileHash | None = None
    reason: Description | None = None
    confidence: Confidence | None = None
    type: Description | None = None
    dhash: PerceptualHash | None = None
    phash: PerceptualHash | None = None
    dhash_distance: int | None = None
    phash_distance: int | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class CrewCreate(CrewBase):
    pass


class CrewUpdate(BaseModel):
    unique_id: UniqueID | None = None
    file1: FileName | None = None
    file2: FileName | None = None
    firstname: PersonName | None = None
    lastname: PersonName | None = None
    airline: PersonName | None = None
    iscrewid: bool | None = None
    createdate: datetime | None = None
    user_id: int | None = Field(default=None, gt=0)
    file1_hash: FileHash | None = None
    file2_hash: FileHash | None = None
    reason: Description | None = None
    confidence: Confidence | None = None
    type: Description | None = None
    dhash: PerceptualHash | None = None
    phash: PerceptualHash | None = None
    dhash_distance: int | None = None
    phash_distance: int | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("unique_id", "iscrewid", "createdate")
    @classmethod
    def reject_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class CrewRead(CrewBase):
    id: int
    user_id: int | None = Field(validation_alias="userid")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

Iso1 = Annotated[str, Field(min_length=2, max_length=2)]
Iso3 = Annotated[str, Field(min_length=3, max_length=3)]
LanguageName = Annotated[str, Field(min_length=1, max_length=150)]


class LanguageCreate(BaseModel):
    iso1: Iso1 | None = None
    iso2b: Iso3 | None = None
    iso2t: Iso3 | None = None
    iso3: Iso3
    name: LanguageName

    model_config = ConfigDict(str_strip_whitespace=True)


class LanguageUpdate(BaseModel):
    iso1: Iso1 | None = None
    iso2b: Iso3 | None = None
    iso2t: Iso3 | None = None
    iso3: Iso3 | None = None
    name: LanguageName | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("iso3", "name")
    @classmethod
    def reject_null_required_fields(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class LanguageRead(BaseModel):
    id: int
    iso1: str | None
    iso2b: str | None
    iso2t: str | None
    iso3: str
    name: str

    model_config = ConfigDict(from_attributes=True)

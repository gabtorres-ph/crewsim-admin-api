from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

PackageSKU = Annotated[str, Field(min_length=1, max_length=255)]
PackageName = Annotated[str, Field(min_length=1, max_length=255)]


class PackageCreate(BaseModel):
    sku: PackageSKU
    name: PackageName | None = None
    price: float | None = None
    points: int | None = None
    sparkid: int | None = None
    reward: int | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class PackageUpdate(BaseModel):
    sku: PackageSKU | None = None
    name: PackageName | None = None
    price: float | None = None
    points: int | None = None
    sparkid: int | None = None
    reward: int | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("sku")
    @classmethod
    def reject_null_sku(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class PackageRead(BaseModel):
    id: int
    sku: str
    name: str | None
    price: float | None
    points: int | None
    sparkid: int | None
    reward: int | None

    model_config = ConfigDict(from_attributes=True)

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

CurrencyCode = Annotated[str, Field(min_length=3, max_length=3)]
CurrencyName = Annotated[str, Field(min_length=1, max_length=100)]
CurrencySymbol = Annotated[str, Field(min_length=1, max_length=10)]
NonnegativeInteger = Annotated[int, Field(ge=0)]
IsoNumeric = Annotated[int, Field(ge=1, le=999)]


class CurrencyCreate(BaseModel):
    code: CurrencyCode
    name: CurrencyName
    symbol: CurrencySymbol
    symbol_native: CurrencySymbol
    decimal_digits: NonnegativeInteger
    rounding: NonnegativeInteger
    iso_numeric: IsoNumeric

    model_config = ConfigDict(str_strip_whitespace=True)


class CurrencyUpdate(BaseModel):
    code: CurrencyCode | None = None
    name: CurrencyName | None = None
    symbol: CurrencySymbol | None = None
    symbol_native: CurrencySymbol | None = None
    decimal_digits: NonnegativeInteger | None = None
    rounding: NonnegativeInteger | None = None
    iso_numeric: IsoNumeric | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator(
        "code", "name", "symbol", "symbol_native", "decimal_digits", "rounding", "iso_numeric"
    )
    @classmethod
    def reject_null_required_fields(cls, value: str | int | None) -> str | int:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class CurrencyRead(BaseModel):
    id: int
    code: str
    name: str
    symbol: str
    symbol_native: str
    decimal_digits: int
    rounding: int
    iso_numeric: int

    model_config = ConfigDict(from_attributes=True)

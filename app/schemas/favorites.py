from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

CountryName = Annotated[str, Field(min_length=1, max_length=255)]


class FavoriteCreate(BaseModel):
    user_id: int = Field(gt=0)
    country: CountryName

    model_config = ConfigDict(str_strip_whitespace=True)


class FavoriteRead(BaseModel):
    id: int
    user_id: int = Field(validation_alias="userid")
    country: str

    model_config = ConfigDict(from_attributes=True)

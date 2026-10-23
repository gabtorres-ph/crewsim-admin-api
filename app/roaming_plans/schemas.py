from pydantic import BaseModel, ConfigDict, Field


class RoamingPlanSnapshot(BaseModel):
    id: int = Field(gt=0)
    roaming_plan_name: str | None = Field(max_length=255)

    model_config = ConfigDict(str_strip_whitespace=True)


class RoamingPlanRefreshResult(BaseModel):
    fetched: int = Field(ge=0)
    created: int = Field(ge=0)
    updated: int = Field(ge=0)
    unchanged: int = Field(ge=0)


class RoamingPlanRead(BaseModel):
    id: int
    roaming_plan_name: str | None

    model_config = ConfigDict(from_attributes=True)

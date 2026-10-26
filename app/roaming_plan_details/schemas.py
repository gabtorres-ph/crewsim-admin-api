from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class RoamingPlanDetailSnapshot(BaseModel):
    roaming_plan_rule_id: int = Field(gt=0)
    roaming_plan_id: int = Field(gt=0)
    network_id: int = Field(gt=0)
    continent: str = Field(max_length=100)
    country_name: str = Field(max_length=100)
    country_iso2: str = Field(min_length=2, max_length=2)
    operator_name: str = Field(max_length=255)
    mcc_mncs: list[dict[str, str]]
    tadigs: list[str]
    active: StrictBool
    data_rate: Decimal = Field(allow_inf_nan=False)
    start_date: datetime

    model_config = ConfigDict(str_strip_whitespace=True)


class RoamingPlanDetailRefreshResult(BaseModel):
    fetched: int = Field(ge=0)
    created: int = Field(ge=0)
    updated: int = Field(ge=0)
    unchanged: int = Field(ge=0)


class RoamingPlanDetailRead(BaseModel):
    roaming_plan_rule_id: int
    roaming_plan_id: int
    network_id: int
    continent: str
    country_name: str
    country_iso2: str
    operator_name: str
    mcc_mncs: list[dict[str, str]]
    tadigs: list[str]
    active: bool
    data_rate: Decimal
    start_date: datetime

    model_config = ConfigDict(from_attributes=True)

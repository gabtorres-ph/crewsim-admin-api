from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

NetworkStatusString = Annotated[str, Field(min_length=1, max_length=255)]
NetworkStatusImsi = Annotated[str, Field(pattern=r"^[0-9]{5,15}$")]


class NetworkStatusBase(BaseModel):
    sim_id: int = Field(gt=0)
    imsi: NetworkStatusImsi
    status: NetworkStatusString
    start: datetime
    end: datetime | None = None
    profile_type: NetworkStatusString
    status_modification: NetworkStatusString

    model_config = ConfigDict(str_strip_whitespace=True)


class NetworkStatusCreate(NetworkStatusBase):
    pass


class NetworkStatusUpdate(BaseModel):
    sim_id: int | None = Field(default=None, gt=0)
    imsi: NetworkStatusImsi | None = None
    status: NetworkStatusString | None = None
    start: datetime | None = None
    end: datetime | None = None
    profile_type: NetworkStatusString | None = None
    status_modification: NetworkStatusString | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator(
        "sim_id",
        "imsi",
        "status",
        "start",
        "profile_type",
        "status_modification",
    )
    @classmethod
    def reject_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class NetworkStatusSnapshot(NetworkStatusBase):
    pass


class NetworkStatusRead(NetworkStatusBase):
    id: int
    sim_id: int = Field(validation_alias="simid", gt=0)
    profile_type: NetworkStatusString = Field(validation_alias="profiletype")
    status_modification: NetworkStatusString = Field(validation_alias="statusmodification")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class NetworkStatusSyncResult(BaseModel):
    fetched: int = Field(ge=0)
    deleted: int = Field(ge=0)
    created: int = Field(ge=0)
    records: list[NetworkStatusRead]

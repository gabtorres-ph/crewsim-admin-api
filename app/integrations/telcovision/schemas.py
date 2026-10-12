import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

IMSI_PATTERN = re.compile(r"^\d{5,15}$")


def _validate_imsi(value: int | str) -> int | str:
    if not IMSI_PATTERN.fullmatch(str(value)):
        raise ValueError("IMSI must contain 5 to 15 digits")
    return value


# Telcovision sends the IMSI as a number on some events and as a string on others. The
# original type is kept so the stored payload matches what the provider sent.
TelcovisionImsi = Annotated[int | str, AfterValidator(_validate_imsi)]


class TelcovisionPayload(BaseModel):
    # Unknown fields are kept so provider additions are stored instead of rejected.
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class TelcovisionEs2Event(TelcovisionPayload):
    imsi: TelcovisionImsi
    iccid: str | None = None
    eid: str | None = None
    subs_id: int | None = Field(default=None, alias="subsId")
    status: str | None = None


class TelcovisionSubscriber(TelcovisionPayload):
    imsi: TelcovisionImsi
    iccid: str | None = None
    msisdn: int | str | None = None
    subscriber_id: int | None = Field(default=None, alias="subscriberId")


class TelcovisionLocationEvent(TelcovisionPayload):
    subscriber: TelcovisionSubscriber
    additional_info: dict[str, object] | None = Field(default=None, alias="additionalInfo")
    mcc: int | str | None = None
    mnc: int | str | None = None


class TelcovisionPrepaidPackage(TelcovisionPayload):
    subscriber_imsi: TelcovisionImsi = Field(alias="subscriberIMSI")
    units_before: int | None = Field(default=None, alias="unitsBefore")
    units_after: int | None = Field(default=None, alias="unitsAfter")
    threshold_percentage: int | str | None = Field(default=None, alias="thresholdPercentage")
    threshold_units: int | str | None = Field(default=None, alias="thresholdUnits")
    subscriber_package_id: int | None = Field(default=None, alias="subscriberPackageId")
    total_units: int | None = Field(default=None, alias="totalUnits")
    subscriber_id: int | None = Field(default=None, alias="subscriberId")
    usage_type: str | None = Field(default=None, alias="usageType")


class TelcovisionPackageEvent(TelcovisionPayload):
    subscriber_prepaid_package: TelcovisionPrepaidPackage = Field(
        alias="subscriberPrepaidPackage"
    )

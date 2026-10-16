import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictBool, StrictInt

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


class TelcovisionResponseModel(BaseModel):
    # Outbound responses ignore undocumented provider fields.
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class TelcovisionAccount(TelcovisionResponseModel):
    id: StrictInt = Field(gt=0)
    name: str
    balance: float = Field(allow_inf_nan=False)
    package_only: StrictBool = Field(alias="packageOnly")
    steering_list_id: StrictInt | None = Field(default=None, alias="steeringListId")


class TelcovisionReseller(TelcovisionResponseModel):
    id: StrictInt = Field(gt=0)
    account: list[TelcovisionAccount]


class TelcovisionAccountList(TelcovisionResponseModel):
    reseller: list[TelcovisionReseller]


class TelcovisionAccountsResponse(TelcovisionResponseModel):
    list_reseller_account: TelcovisionAccountList = Field(alias="listResellerAccount")


class TelcovisionSubscriberImsi(TelcovisionResponseModel):
    imsi: TelcovisionImsi


class TelcovisionSubscriberStatus(TelcovisionResponseModel):
    id: StrictInt = Field(gt=0)
    status: str = Field(min_length=1, max_length=255)


class TelcovisionSubscriberSim(TelcovisionResponseModel):
    esim: StrictBool
    smdp_server: str | None = Field(default=None, alias="smdpServer", max_length=255)
    activation_code: str | None = Field(default=None, alias="activationCode", max_length=255)


class TelcovisionListedSubscriber(TelcovisionResponseModel):
    imsi_list: list[TelcovisionSubscriberImsi] = Field(alias="imsiList", min_length=1)
    status: list[TelcovisionSubscriberStatus]
    sim: TelcovisionSubscriberSim
    account_id: StrictInt = Field(alias="accountId", gt=0)
    balance: float | None = Field(default=None, allow_inf_nan=False)
    use_account_for_charging: StrictBool = Field(alias="useAccountForCharging")
    allowed_data: StrictBool = Field(alias="allowedData")
    mobile_plan_id: StrictInt | None = Field(default=None, alias="mobilePlanId", gt=0)
    # TODO convert offset-aware dates to naive UTC (or switch the esims columns to
    # DateTime(timezone=True)); the naive DateTime columns currently store them in the
    # Postgres session timezone
    activation_date: datetime | None = Field(default=None, alias="activationDate")
    last_usage_date: datetime | None = Field(default=None, alias="lastUsageDate")


class TelcovisionSubscriberList(TelcovisionResponseModel):
    subscriber_list: list[TelcovisionListedSubscriber] = Field(alias="subscriberList")
    has_more: StrictBool = Field(alias="hasMore")
    nb_found: StrictInt = Field(alias="nbFound", ge=0)


class TelcovisionSubscribersResponse(TelcovisionResponseModel):
    list_subscriber: TelcovisionSubscriberList = Field(alias="listSubscriber")

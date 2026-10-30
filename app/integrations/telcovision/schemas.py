import re
from datetime import datetime
from decimal import Decimal
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


class TelcovisionSubscriberNetworkInfo(TelcovisionResponseModel):
    time: datetime | None = None
    last_mcc: int | str | None = Field(default=None, alias="lastMcc")
    last_mnc: int | str | None = Field(default=None, alias="lastMnc")
    last_cell_id: StrictInt | None = Field(default=None, alias="lastCellId")
    last_lac: StrictInt | None = Field(default=None, alias="lastLac")
    last_imei: str | None = Field(default=None, alias="lastImei", max_length=255)
    last_rat: str | None = Field(default=None, alias="lastRat", max_length=255)
    model: str | None = Field(default=None, max_length=255)


class TelcovisionSingleSubscriber(TelcovisionResponseModel):
    imsi_list: list[TelcovisionSubscriberImsi] | None = Field(default=None, alias="imsiList")
    status: list[TelcovisionSubscriberStatus] | None = None
    account_id: StrictInt | None = Field(default=None, alias="accountId", gt=0)
    balance: float | None = Field(default=None, allow_inf_nan=False)
    use_account_for_charging: StrictBool | None = Field(
        default=None, alias="useAccountForCharging"
    )
    allowed_data: StrictBool | None = Field(default=None, alias="allowedData")
    mobile_plan_id: StrictInt | None = Field(default=None, alias="mobilePlanId", gt=0)
    activation_date: datetime | None = Field(default=None, alias="activationDate")
    last_usage_date: datetime | None = Field(default=None, alias="lastUsageDate")
    network_info: TelcovisionSubscriberNetworkInfo | None = Field(
        default=None, alias="networkInfo"
    )


class TelcovisionSingleSubscriberResponse(TelcovisionResponseModel):
    get_single_subscriber: TelcovisionSingleSubscriber = Field(alias="getSingleSubscriber")


class TelcovisionSubscriberList(TelcovisionResponseModel):
    subscriber_list: list[TelcovisionListedSubscriber] = Field(alias="subscriberList")
    has_more: StrictBool = Field(alias="hasMore")
    nb_found: StrictInt = Field(alias="nbFound", ge=0)


class TelcovisionSubscribersResponse(TelcovisionResponseModel):
    list_subscriber: TelcovisionSubscriberList = Field(alias="listSubscriber")


class TelcovisionSubscriberMoveResponse(TelcovisionResponseModel):
    moved_count: StrictInt = Field(alias="moveSubscriberRangeToAccount", ge=0)


class TelcovisionSimProviderStatus(TelcovisionResponseModel):
    sim_id: StrictInt = Field(alias="simId", gt=0)
    status: str = Field(min_length=1, max_length=255)
    start: datetime
    end: datetime | None = None
    profile_type: str = Field(alias="profileType", min_length=1, max_length=255)
    status_modification: str = Field(
        alias="statusModification", min_length=1, max_length=255
    )


class TelcovisionSimProviderStatusResponse(TelcovisionResponseModel):
    get_sim_provider_status: list[TelcovisionSimProviderStatus] = Field(
        alias="getSimProviderStatus"
    )


class TelcovisionSubscriberTariff(TelcovisionResponseModel):
    roaming_plan_id: StrictInt = Field(alias="roamingplanid", gt=0)
    roaming_plan_name: str = Field(alias="roamingplanname", max_length=255)


class TelcovisionSubscriberTariffList(TelcovisionResponseModel):
    tariffs: list[TelcovisionSubscriberTariff] = Field(alias="tariff")


class TelcovisionSubscriberTariffResponse(TelcovisionResponseModel):
    list_subscriber_tariff: TelcovisionSubscriberTariffList = Field(alias="listSubscriberTariff")


class TelcovisionMccMnc(TelcovisionResponseModel):
    mcc: str = Field(min_length=1)
    mnc: str = Field(min_length=1)


class TelcovisionTariffRuleOperator(TelcovisionResponseModel):
    network_id: StrictInt = Field(alias="networkId", gt=0)
    continent: str = Field(max_length=100)
    country_name: str = Field(alias="countryName", max_length=100)
    country_iso2: str = Field(alias="countryIso2", min_length=2, max_length=2)
    operator_name: str = Field(alias="operatorName", max_length=255)
    mcc_mncs: list[TelcovisionMccMnc] = Field(alias="mccMncs")
    tadigs: list[str]


class TelcovisionTariffRule(TelcovisionResponseModel):
    operator: TelcovisionTariffRuleOperator
    roaming_plan_rule_id: StrictInt = Field(alias="roamingplanruleid", gt=0)
    roaming_plan_id: StrictInt = Field(alias="roamingplanid", gt=0)
    network_id: StrictInt = Field(alias="networkid", gt=0)
    active: StrictBool
    data_rate: Decimal | None = Field(default=None, alias="datarate", allow_inf_nan=False)
    start_date: datetime = Field(alias="startdate")


class TelcovisionTariffRuleList(TelcovisionResponseModel):
    rules: list[TelcovisionTariffRule] = Field(alias="rule")


class TelcovisionTariffRuleResponse(TelcovisionResponseModel):
    list_tariff_rule: TelcovisionTariffRuleList = Field(alias="listTariffRule")

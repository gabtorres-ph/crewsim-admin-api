import pytest
from pydantic import ValidationError

from app.integrations.telcovision.mapper import (
    es2_to_sim_notification,
    location_to_sim_notification,
    package_to_sim_notification,
)
from app.integrations.telcovision.schemas import (
    TelcovisionEs2Event,
    TelcovisionLocationEvent,
    TelcovisionPackageEvent,
)
from app.sim_notifications.models import SimNotificationProvider, SimNotificationType

ES2_PAYLOAD = {
    "iccid": "12334567891234546",
    "imsi": "123456789123456",
    "eid": "89049032004008882600007171733779",
    "subsId": 4,
    "status": "Enable",
}
LOCATION_PAYLOAD = {
    "subscriber": {
        "imsi": 260010180730303,
        "iccid": "8948010000086464138",
        "msisdn": 48812635303,
        "subscriberId": 38406164,
    },
    "additionalInfo": {"sponsorCode": "SP05"},
    "mcc": 404,
    "mnc": 14,
}
PACKAGE_PAYLOAD = {
    "subscriberPrepaidPackage": {
        "unitsBefore": 1000000,
        "unitsAfter": 2000000,
        "thresholdPercentage": "80",
        "thresholdUnits": "1500000",
        "subscriberPackageId": 123,
        "totalUnits": 2300000,
        "subscriberId": 123,
        "subscriberIMSI": "123456789",
        "usageType": "DATA",
    }
}


def test_es2_event_maps_to_sim_notification() -> None:
    notification = es2_to_sim_notification(TelcovisionEs2Event.model_validate(ES2_PAYLOAD))

    assert notification.typ == SimNotificationType.ES2
    assert notification.imsi == "123456789123456"
    assert notification.provider == SimNotificationProvider.TELCOVISION
    assert notification.payload == ES2_PAYLOAD
    assert notification.createdate is None


def test_location_event_maps_numeric_imsi_and_keeps_raw_payload() -> None:
    notification = location_to_sim_notification(
        TelcovisionLocationEvent.model_validate(LOCATION_PAYLOAD)
    )

    assert notification.typ == SimNotificationType.LOCATION
    assert notification.imsi == "260010180730303"
    assert notification.payload == LOCATION_PAYLOAD


def test_package_event_maps_nested_imsi() -> None:
    notification = package_to_sim_notification(
        TelcovisionPackageEvent.model_validate(PACKAGE_PAYLOAD)
    )

    assert notification.typ == SimNotificationType.PACKAGE
    assert notification.imsi == "123456789"
    assert notification.payload == PACKAGE_PAYLOAD


def test_unknown_fields_are_preserved_in_payload() -> None:
    payload = {**ES2_PAYLOAD, "newField": {"nested": True}}

    notification = es2_to_sim_notification(TelcovisionEs2Event.model_validate(payload))

    assert notification.payload == payload


@pytest.mark.parametrize("imsi", ["", "1234", "1234567890123456", "12345abc"])
def test_invalid_imsi_is_rejected(imsi: str) -> None:
    with pytest.raises(ValidationError, match="IMSI must contain 5 to 15 digits"):
        TelcovisionEs2Event.model_validate({**ES2_PAYLOAD, "imsi": imsi})


def test_missing_imsi_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TelcovisionLocationEvent.model_validate({"mcc": 404, "mnc": 14, "subscriber": {}})

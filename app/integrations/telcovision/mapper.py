from app.integrations.telcovision.schemas import (
    TelcovisionEs2Event,
    TelcovisionLocationEvent,
    TelcovisionPackageEvent,
    TelcovisionPayload,
)
from app.sim_notifications.models import SimNotificationProvider, SimNotificationType
from app.sim_notifications.schemas import SimNotificationCreate


def _to_sim_notification(
    event: TelcovisionPayload, typ: SimNotificationType, imsi: int | str
) -> SimNotificationCreate:
    return SimNotificationCreate(
        typ=typ,
        imsi=str(imsi),
        provider=SimNotificationProvider.TELCOVISION,
        # exclude_unset keeps the stored payload identical to the body that was received.
        payload=event.model_dump(mode="json", by_alias=True, exclude_unset=True),
    )


def es2_to_sim_notification(event: TelcovisionEs2Event) -> SimNotificationCreate:
    return _to_sim_notification(event, SimNotificationType.ES2, event.imsi)


def location_to_sim_notification(event: TelcovisionLocationEvent) -> SimNotificationCreate:
    return _to_sim_notification(event, SimNotificationType.LOCATION, event.subscriber.imsi)


def package_to_sim_notification(event: TelcovisionPackageEvent) -> SimNotificationCreate:
    return _to_sim_notification(
        event,
        SimNotificationType.PACKAGE,
        event.subscriber_prepaid_package.subscriber_imsi,
    )

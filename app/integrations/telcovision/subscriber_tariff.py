import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.redis.outbound_logging import OutboundExchange
from app.integrations.telcovision.client import (
    TelcovisionError,
    open_telcovision_client,
)
from app.integrations.telcovision.schemas import TelcovisionSubscriberTariffResponse
from app.roaming_plans.manager import RoamingPlanManager
from app.roaming_plans.schemas import RoamingPlanRefreshResult, RoamingPlanSnapshot

logger = logging.getLogger(__name__)


def parse_subscriber_tariff_snapshot(payload: dict[str, object]) -> list[RoamingPlanSnapshot]:
    """Flatten a listSubscriberTariff response; invalid records reject the whole snapshot."""
    try:
        response = TelcovisionSubscriberTariffResponse.model_validate(payload)
        snapshots = [
            RoamingPlanSnapshot(
                id=tariff.roaming_plan_id,
                roaming_plan_name=tariff.roaming_plan_name,
            )
            for tariff in response.list_subscriber_tariff.tariffs
        ]
    except ValidationError:
        raise TelcovisionError("invalid_response") from None

    if len({snapshot.id for snapshot in snapshots}) != len(snapshots):
        raise TelcovisionError("duplicate_roaming_plan_id")
    return snapshots


def refresh_telcovision_subscriber_tariffs(
    session: Session,
    settings: Settings,
    *,
    request_id: str,
    outbound_exchanges: list[OutboundExchange],
) -> RoamingPlanRefreshResult:
    """Fetch Telcovision subscriber tariffs and mirror them into roaming_plans."""
    with open_telcovision_client(
        settings, request_id=request_id, outbound_exchanges=outbound_exchanges
    ) as client:
        logger.info("Telcovision subscriber tariff refresh started request_id=%s", request_id)

        def load_snapshot() -> list[RoamingPlanSnapshot]:
            snapshots = parse_subscriber_tariff_snapshot(
                client.list_subscriber_tariff(validate=parse_subscriber_tariff_snapshot)
            )
            logger.info(
                "Telcovision subscriber tariff snapshot parsed request_id=%s plans=%d",
                request_id,
                len(snapshots),
            )
            return snapshots

        return RoamingPlanManager(session).refresh_roaming_plans(load_snapshot)

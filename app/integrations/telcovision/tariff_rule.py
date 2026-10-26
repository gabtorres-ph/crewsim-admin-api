import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.redis.outbound_logging import OutboundExchange
from app.integrations.telcovision.client import (
    TelcovisionError,
    open_telcovision_client,
)
from app.integrations.telcovision.schemas import TelcovisionTariffRuleResponse
from app.roaming_plan_details.manager import RoamingPlanDetailManager
from app.roaming_plan_details.schemas import (
    RoamingPlanDetailRefreshResult,
    RoamingPlanDetailSnapshot,
)

logger = logging.getLogger(__name__)


def parse_tariff_rule_snapshot(payload: dict[str, object]) -> list[RoamingPlanDetailSnapshot]:
    """Map a listTariffRule response; invalid records reject the whole snapshot."""
    try:
        response = TelcovisionTariffRuleResponse.model_validate(payload)
        snapshots = [
            RoamingPlanDetailSnapshot(
                roaming_plan_rule_id=rule.roaming_plan_rule_id,
                roaming_plan_id=rule.roaming_plan_id,
                network_id=rule.network_id,
                continent=rule.operator.continent,
                country_name=rule.operator.country_name,
                country_iso2=rule.operator.country_iso2,
                operator_name=rule.operator.operator_name,
                mcc_mncs=[mcc_mnc.model_dump() for mcc_mnc in rule.operator.mcc_mncs],
                tadigs=rule.operator.tadigs,
                active=rule.active,
                data_rate=rule.data_rate,
                start_date=rule.start_date,
            )
            for rule in response.list_tariff_rule.rules
        ]
    except ValidationError:
        raise TelcovisionError("invalid_response") from None

    if len({snapshot.roaming_plan_rule_id for snapshot in snapshots}) != len(snapshots):
        raise TelcovisionError("duplicate_roaming_plan_rule_id")
    return snapshots


def refresh_telcovision_tariff_rules(
    session: Session,
    settings: Settings,
    tariff_id: int,
    *,
    request_id: str,
    outbound_exchanges: list[OutboundExchange],
) -> RoamingPlanDetailRefreshResult:
    """Fetch Telcovision tariff rules and upsert them into roaming_plan_details."""
    with open_telcovision_client(
        settings, request_id=request_id, outbound_exchanges=outbound_exchanges
    ) as client:
        logger.info(
            "Telcovision tariff rule refresh started request_id=%s tariff_id=%s",
            request_id,
            tariff_id,
        )

        def load_snapshot() -> list[RoamingPlanDetailSnapshot]:
            snapshots = parse_tariff_rule_snapshot(
                client.list_tariff_rules(tariff_id, validate=parse_tariff_rule_snapshot)
            )
            logger.info(
                "Telcovision tariff rule snapshot parsed request_id=%s tariff_id=%s rules=%d",
                request_id,
                tariff_id,
                len(snapshots),
            )
            return snapshots

        return RoamingPlanDetailManager(session).refresh_roaming_plan_details(load_snapshot)

import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.redis.outbound_logging import OutboundExchange
from app.integrations.telcovision.client import (
    TelcovisionError,
    TelcovisionNotConfiguredError,
    open_telcovision_client,
)
from app.integrations.telcovision.schemas import TelcovisionTariffRuleResponse
from app.roaming_plan_details.manager import RoamingPlanDetailManager
from app.roaming_plan_details.schemas import (
    RoamingPlanDetailRefreshResult,
    RoamingPlanDetailSnapshot,
)

logger = logging.getLogger(__name__)


def parse_tariff_rule_snapshot(
    payload: dict[str, object],
) -> list[RoamingPlanDetailSnapshot]:
    """Map tariff rules using each rule's provider-supplied roaming plan ID."""
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
    *,
    tariff_id: int | None = None,
    request_id: str,
    outbound_exchanges: list[OutboundExchange],
) -> RoamingPlanDetailRefreshResult:
    """Fetch selected tariff rules and upsert their roaming-plan details."""
    if tariff_id is None:
        selected_provider_id = settings.telcovision_carrier_rateid
        provider_id_name = "carrier_rateid"
        operation = "getCustomerTariff"
    else:
        selected_provider_id = tariff_id
        provider_id_name = "tariff_id"
        operation = "listTariffRule"

    if selected_provider_id is None:
        logger.error(
            "Telcovision carrier rate refresh not configured request_id=%s",
            request_id,
        )
        raise TelcovisionNotConfiguredError

    with open_telcovision_client(
        settings, request_id=request_id, outbound_exchanges=outbound_exchanges
    ) as client:
        logger.info(
            "Telcovision tariff rule refresh started request_id=%s operation=%s %s=%s",
            request_id,
            operation,
            provider_id_name,
            selected_provider_id,
        )

        def parse_selected_tariff_snapshot(
            payload: dict[str, object],
        ) -> list[RoamingPlanDetailSnapshot]:
            return parse_tariff_rule_snapshot(payload)

        def load_snapshot() -> list[RoamingPlanDetailSnapshot]:
            if tariff_id is None:
                payload = client.get_customer_tariff(
                    selected_provider_id,
                    validate=parse_selected_tariff_snapshot,
                )
            else:
                payload = client.list_tariff_rules(
                    selected_provider_id,
                    validate=parse_selected_tariff_snapshot,
                )

            snapshots = parse_selected_tariff_snapshot(payload)
            logger.info(
                "Telcovision tariff rule snapshot parsed request_id=%s operation=%s "
                "%s=%s rules=%d",
                request_id,
                operation,
                provider_id_name,
                selected_provider_id,
                len(snapshots),
            )
            return snapshots

        return RoamingPlanDetailManager(session).refresh_roaming_plan_details(load_snapshot)

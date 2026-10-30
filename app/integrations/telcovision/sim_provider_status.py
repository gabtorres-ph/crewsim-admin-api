import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.redis.outbound_logging import OutboundExchange
from app.integrations.telcovision.client import TelcovisionError, open_telcovision_client
from app.integrations.telcovision.schemas import TelcovisionSimProviderStatusResponse
from app.network_status.manager import NetworkStatusManager
from app.network_status.schemas import NetworkStatusSnapshot, NetworkStatusSyncResult

logger = logging.getLogger(__name__)


def parse_sim_provider_status(
    payload: dict[str, object], *, imsi: str, sim_id: int
) -> list[NetworkStatusSnapshot]:
    """Map a getSimProviderStatus response to one IMSI's status history."""
    try:
        response = TelcovisionSimProviderStatusResponse.model_validate(payload)
        snapshots = [
            NetworkStatusSnapshot(
                sim_id=item.sim_id,
                imsi=imsi,
                status=item.status,
                start=item.start,
                end=item.end,
                profile_type=item.profile_type,
                status_modification=item.status_modification,
            )
            for item in response.get_sim_provider_status
        ]
    except ValidationError:
        raise TelcovisionError("invalid_response") from None

    if any(snapshot.sim_id != sim_id for snapshot in snapshots):
        raise TelcovisionError("invalid_response")
    if len({(snapshot.sim_id, snapshot.start) for snapshot in snapshots}) != len(snapshots):
        raise TelcovisionError("invalid_response")
    return snapshots


def sync_telcovision_sim_provider_status(
    session: Session,
    settings: Settings,
    *,
    imsi: str,
    sim_id: int,
    request_id: str,
    outbound_exchanges: list[OutboundExchange],
) -> NetworkStatusSyncResult:
    """Fetch and store one SIM's provider status history."""
    with open_telcovision_client(
        settings, request_id=request_id, outbound_exchanges=outbound_exchanges
    ) as client:
        logger.info(
            "Telcovision SIM provider status sync started request_id=%s imsi=%s sim_id=%s",
            request_id,
            imsi,
            sim_id,
        )

        def parse_snapshot(payload: dict[str, object]) -> list[NetworkStatusSnapshot]:
            return parse_sim_provider_status(payload, imsi=imsi, sim_id=sim_id)

        def load_snapshot() -> list[NetworkStatusSnapshot]:
            snapshots = parse_snapshot(
                client.get_sim_provider_status(sim_id, validate=parse_snapshot)
            )
            logger.info(
                "Telcovision SIM provider status snapshot parsed request_id=%s imsi=%s "
                "sim_id=%s statuses=%d",
                request_id,
                imsi,
                sim_id,
                len(snapshots),
            )
            return snapshots

        return NetworkStatusManager(session).sync_network_status(imsi, sim_id, load_snapshot)

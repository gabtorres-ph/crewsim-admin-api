from pydantic import ValidationError

from app.integrations.telcovision.client import TelcovisionError
from app.integrations.telcovision.schemas import TelcovisionSimProviderStatusResponse
from app.network_status.schemas import NetworkStatusSnapshot


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
    return sorted(snapshots, key=lambda snapshot: snapshot.start, reverse=True)

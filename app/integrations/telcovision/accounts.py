import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.accounts.manager import AccountManager
from app.accounts.schemas import AccountRefreshResult, AccountSnapshot
from app.config import Settings
from app.integrations.redis.outbound_logging import OutboundExchange
# TODO import TelcovisionNotConfiguredError from client in app/accounts/routes.py and drop
# this re-export (ruff PLC0414); also run ruff --fix for the unsorted imports (I001)
from app.integrations.telcovision.client import (
    TelcovisionError,
    TelcovisionNotConfiguredError as TelcovisionNotConfiguredError,
    open_telcovision_client,
)
from app.integrations.telcovision.schemas import TelcovisionAccountsResponse

logger = logging.getLogger(__name__)


def parse_account_snapshot(payload: dict[str, object]) -> list[AccountSnapshot]:
    """Flatten a full listResellerAccount response; any invalid element rejects the whole snapshot."""
    try:
        response = TelcovisionAccountsResponse.model_validate(payload)
        snapshots = [
            AccountSnapshot(
                id=account.id,
                reseller_id=reseller.id,
                name=account.name,
                balance=account.balance,
                package_only=account.package_only,
                steering_list_id=account.steering_list_id,
            )
            for reseller in response.list_reseller_account.reseller
            for account in reseller.account
        ]
    except ValidationError:
        # Validation messages echo provider values, so only a category is propagated.
        raise TelcovisionError("invalid_response") from None

    if len({snapshot.id for snapshot in snapshots}) != len(snapshots):
        raise TelcovisionError("duplicate_account_id")
    return snapshots


def refresh_telcovision_accounts(
    session: Session,
    settings: Settings,
    *,
    request_id: str,
    outbound_exchanges: list[OutboundExchange],
) -> AccountRefreshResult:
    """Fetch a live Telcovision account snapshot and mirror it into the accounts table."""
    with open_telcovision_client(
        settings, request_id=request_id, outbound_exchanges=outbound_exchanges
    ) as client:
        logger.info("Telcovision accounts refresh started request_id=%s", request_id)

        def load_snapshot() -> list[AccountSnapshot]:
            snapshots = parse_account_snapshot(
                client.list_reseller_accounts(validate=parse_account_snapshot)
            )
            logger.info(
                "Telcovision accounts snapshot parsed request_id=%s accounts=%d",
                request_id,
                len(snapshots),
            )
            return snapshots

        return AccountManager(session).refresh_accounts(load_snapshot)

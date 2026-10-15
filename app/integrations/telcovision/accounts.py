import logging
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, ValidationError
from sqlalchemy.orm import Session

from app.accounts.manager import AccountManager
from app.accounts.schemas import AccountRefreshResult, AccountSnapshot
from app.config import Settings
from app.integrations.telcovision.cache import TelcovisionCache
from app.integrations.telcovision.client import (
    TelcovisionClient,
    TelcovisionError,
    build_http_client,
)

logger = logging.getLogger(__name__)


class TelcovisionNotConfiguredError(Exception):
    """The provider URL or token is missing from the environment."""


class _ProviderAccount(BaseModel):
    # Undocumented provider fields are ignored; the fields we store are strictly typed.
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: StrictInt = Field(gt=0)
    name: str
    balance: float = Field(allow_inf_nan=False)
    package_only: StrictBool = Field(alias="packageOnly")
    steering_list_id: StrictInt | None = Field(default=None, alias="steeringListId")


class _ProviderReseller(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: StrictInt = Field(gt=0)
    account: list[_ProviderAccount]


class _ProviderAccountList(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reseller: list[_ProviderReseller]


class _ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    list_reseller_account: _ProviderAccountList = Field(alias="listResellerAccount")


def parse_account_snapshot(payload: dict[str, object]) -> list[AccountSnapshot]:
    """Flatten a full listResellerAccount response; any invalid element rejects the whole snapshot."""
    try:
        response = _ProviderResponse.model_validate(payload)
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
    session: Session, settings: Settings, *, force: bool = False
) -> AccountRefreshResult:
    """Fetch the full Telcovision account snapshot and mirror it into the accounts table.

    The provider response is cached briefly; `force` skips the cache read and refreshes the entry.
    """
    request_id = uuid4().hex[:12]
    api_url = settings.telcovision_api_url
    token = settings.telcovision_api_token.get_secret_value()
    if not api_url or not token:
        logger.error("Telcovision refresh not configured request_id=%s", request_id)
        raise TelcovisionNotConfiguredError

    logger.info("Telcovision accounts refresh started request_id=%s force=%s", request_id, force)
    cache = TelcovisionCache.from_settings(settings, scope=api_url)

    def load_snapshot() -> list[AccountSnapshot]:
        snapshots = parse_account_snapshot(
            client.list_reseller_accounts(bypass_cache=force, validate=parse_account_snapshot)
        )
        logger.info(
            "Telcovision accounts snapshot parsed request_id=%s accounts=%d",
            request_id,
            len(snapshots),
        )
        return snapshots

    with build_http_client() as http_client:
        client = TelcovisionClient(api_url, token, http_client, cache, request_id)
        return AccountManager(session).refresh_accounts(load_snapshot)

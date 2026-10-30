import logging
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from urllib.parse import urlsplit

import httpx

from app.config import Settings
from app.integrations.outbound_http import logged_request
from app.integrations.redis.outbound_logging import OutboundExchange

logger = logging.getLogger(__name__)

# httpx logs every request URL at INFO, and the provider token travels in the query string.
logging.getLogger("httpx").setLevel(logging.WARNING)

CONNECT_TIMEOUT_SECONDS = 10.0
READ_TIMEOUT_SECONDS = 30.0


def build_http_client() -> httpx.Client:
    """Create the bounded HTTP client used for Telcovision calls; callers must close it."""
    return httpx.Client(
        timeout=httpx.Timeout(READ_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS)
    )


class TelcovisionNotConfiguredError(Exception):
    """The provider URL or token is missing from the environment."""


class TelcovisionError(Exception):
    """Safe provider failure; carries only a category and optional provider status code."""

    def __init__(self, category: str, provider_code: int | None = None) -> None:
        super().__init__(category)
        self.category = category
        self.provider_code = provider_code


class TelcovisionClient:
    """Shared transport for Telcovision OCS operations."""

    def __init__(
        self,
        api_url: str,
        token: str,
        http_client: httpx.Client,
        request_id: str,
        outbound_exchanges: list[OutboundExchange],
    ) -> None:
        self._api_url = api_url
        self._token = token
        self._http_client = http_client
        self.request_id = request_id
        self._outbound_exchanges = outbound_exchanges
        self._outbound_start_index = len(outbound_exchanges)
        # Only host and path are logged; the query string carries the token.
        parts = urlsplit(api_url)
        self._log_target = f"{parts.hostname or 'unknown'}{parts.path}"

    def _request(
        self,
        operation: str,
        payload: object,
        *,
        validate: Callable[[dict[str, object]], object] | None = None,
    ) -> dict[str, object]:
        """Return a provider body; `validate` must raise TelcovisionError for unusable shapes."""
        return self._send(operation, payload, validate)

    def _fail(
        self,
        operation: str,
        category: str,
        started_at: float,
        *,
        level: int = logging.ERROR,
        **fields: object,
    ) -> TelcovisionError:
        if len(self._outbound_exchanges) > self._outbound_start_index:
            exchange = self._outbound_exchanges[-1]
            if exchange["request_id"] == self.request_id and exchange["operation"] == operation:
                if category != "transport":
                    exchange["error_category"] = category
                if exchange["outcome"] == "ok":
                    exchange["outcome"] = "provider_error"
        details = "".join(f" {name}={value}" for name, value in fields.items())
        logger.log(
            level,
            "Telcovision request failed request_id=%s operation=%s category=%s duration_ms=%.0f%s",
            self.request_id,
            operation,
            category,
            (time.perf_counter() - started_at) * 1000,
            details,
        )
        provider_code = fields.get("provider_code")
        return TelcovisionError(category, provider_code if isinstance(provider_code, int) else None)

    def _send(
        self,
        operation: str,
        payload: object,
        validate: Callable[[dict[str, object]], object] | None,
    ) -> dict[str, object]:
        logger.info(
            "Telcovision request started request_id=%s operation=%s target=%s",
            self.request_id,
            operation,
            self._log_target,
        )
        started_at = time.perf_counter()
        self._outbound_start_index = len(self._outbound_exchanges)
        # Exception text from httpx can include the token-bearing URL, so it is never propagated
        # or logged; only the exception class name is.
        try:
            response = logged_request(
                self._http_client,
                "POST",
                self._api_url,
                operation=operation,
                request_id=self.request_id,
                exchanges=self._outbound_exchanges,
                params={"token": self._token},
                json={operation: payload},
                headers={"Content-Type": "application/json"},
            )
        except httpx.RequestError as error:
            raise self._fail(
                operation, "transport", started_at, error=type(error).__name__
            ) from None

        size = len(response.content)
        if not response.is_success:
            raise self._fail(
                operation, "http_status", started_at, http_status=response.status_code, bytes=size
            )

        content_type = response.headers.get("content-type", "unknown")
        try:
            body = response.json()
        except ValueError:
            raise self._fail(
                operation,
                "invalid_json",
                started_at,
                http_status=response.status_code,
                content_type=content_type,
                bytes=size,
            ) from None
        if not isinstance(body, dict):
            raise self._fail(
                operation,
                "invalid_response",
                started_at,
                http_status=response.status_code,
                content_type=content_type,
                bytes=size,
            )

        status = body.get("status")
        code = status.get("code") if isinstance(status, dict) else None
        if isinstance(code, bool) or not isinstance(code, int | float):
            raise self._fail(
                operation,
                "invalid_response",
                started_at,
                http_status=response.status_code,
                bytes=size,
            )
        if code != 0:
            raise self._fail(
                operation,
                "provider_status",
                started_at,
                level=logging.WARNING,
                provider_code=int(code),
            )

        if validate is not None:
            try:
                validate(body)
            except TelcovisionError as error:
                raise self._fail(
                    operation, error.category, started_at, http_status=response.status_code
                ) from None

        logger.info(
            "Telcovision request succeeded request_id=%s operation=%s http_status=%s "
            "duration_ms=%.0f bytes=%s",
            self.request_id,
            operation,
            response.status_code,
            (time.perf_counter() - started_at) * 1000,
            size,
        )
        return body

    def list_reseller_accounts(
        self,
        *,
        validate: Callable[[dict[str, object]], object] | None = None,
    ) -> dict[str, object]:
        return self._request("listResellerAccount", {}, validate=validate)

    def list_subscribers(
        self,
        account_id: int,
        *,
        validate: Callable[[dict[str, object]], object] | None = None,
    ) -> dict[str, object]:
        """Request subscribers for one account through the shared transport."""
        return self._request("listSubscriber", {"accountId": str(account_id)}, validate=validate)

    def get_single_subscriber(
        self,
        imsi: str,
        *,
        validate: Callable[[dict[str, object]], object] | None = None,
    ) -> dict[str, object]:

        return self._request("getSingleSubscriber", {"imsi": str(imsi)}, validate=validate)

    def get_sim_provider_status(
        self,
        sim_id: int,
        *,
        validate: Callable[[dict[str, object]], object] | None = None,
    ) -> dict[str, object]:
        return self._request("getSimProviderStatus", sim_id, validate=validate)

    def move_subscriber_range_to_account(
        self,
        range_start: str,
        range_end: str,
        src_account: int,
        dst_account: int,
        *,
        validate: Callable[[dict[str, object]], object] | None = None,
    ) -> dict[str, object]:
        return self._request(
            "moveSubscriberRangeToAccount",
            {
                "rangeType": "IMSI",
                "rangeStart": range_start,
                "rangeEnd": range_end,
                "srcAccountId": src_account,
                "destAccount": dst_account,
            },
            validate=validate,
        )

    def list_subscriber_tariff(
        self,
        *,
        validate: Callable[[dict[str, object]], object] | None = None,
    ) -> dict[str, object]:
        return self._request("listSubscriberTariff", {}, validate=validate)

    def list_tariff_rules(
        self,
        tariff_id: int,
        *,
        validate: Callable[[dict[str, object]], object] | None = None,
    ) -> dict[str, object]:
        return self._request("listTariffRule", tariff_id, validate=validate)

    def get_customer_tariff(
        self,
        carrier_rateid: int,
        *,
        validate: Callable[[dict[str, object]], object] | None = None,
    ) -> dict[str, object]:
        return self._request("getCustomerTariff", carrier_rateid, validate=validate)


@contextmanager
def open_telcovision_client(
    settings: Settings,
    *,
    request_id: str,
    outbound_exchanges: list[OutboundExchange],
) -> Iterator[TelcovisionClient]:
    """Check provider credentials and close the bounded HTTP client after use."""
    api_url = settings.telcovision_api_url
    token = settings.telcovision_api_token.get_secret_value()
    if not api_url or not token:
        logger.error("Telcovision refresh not configured request_id=%s", request_id)
        raise TelcovisionNotConfiguredError

    with build_http_client() as http_client:
        yield TelcovisionClient(api_url, token, http_client, request_id, outbound_exchanges)

import logging
import time
from collections.abc import Callable
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from app.integrations.telcovision.cache import TelcovisionCache

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
        cache: TelcovisionCache | None = None,
        request_id: str | None = None,
    ) -> None:
        self._api_url = api_url
        self._token = token
        self._http_client = http_client
        self._cache = cache
        self.request_id = request_id or uuid4().hex[:12]
        # Only host and path are logged; the query string carries the token.
        parts = urlsplit(api_url)
        self._log_target = f"{parts.hostname or 'unknown'}{parts.path}"

    def _request(
        self,
        operation: str,
        payload: dict[str, object],
        *,
        bypass_cache: bool = False,
        validate: Callable[[dict[str, object]], object] | None = None,
    ) -> dict[str, object]:
        """Return a provider body; `validate` must raise TelcovisionError for unusable shapes."""
        if self._cache is None:
            return self._send(operation, payload, validate)
        return self._cache.fetch(
            operation,
            payload,
            lambda: self._send(operation, payload, validate),
            request_id=self.request_id,
            bypass=bypass_cache,
            validate=validate,
        )

    def _fail(
        self,
        operation: str,
        category: str,
        started_at: float,
        *,
        level: int = logging.ERROR,
        **fields: object,
    ) -> TelcovisionError:
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
        payload: dict[str, object],
        validate: Callable[[dict[str, object]], object] | None,
    ) -> dict[str, object]:
        logger.info(
            "Telcovision request started request_id=%s operation=%s target=%s",
            self.request_id,
            operation,
            self._log_target,
        )
        started_at = time.perf_counter()
        # Exception text from httpx can include the token-bearing URL, so it is never propagated
        # or logged; only the exception class name is.
        try:
            response = self._http_client.post(
                self._api_url,
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
        bypass_cache: bool = False,
        validate: Callable[[dict[str, object]], object] | None = None,
    ) -> dict[str, object]:
        return self._request(
            "listResellerAccount", {}, bypass_cache=bypass_cache, validate=validate
        )

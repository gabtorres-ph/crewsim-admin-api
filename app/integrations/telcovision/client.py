import httpx

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

    def __init__(self, api_url: str, token: str, http_client: httpx.Client) -> None:
        self._api_url = api_url
        self._token = token
        self._http_client = http_client

    def _request(self, operation: str, payload: dict[str, object]) -> dict[str, object]:
        # Exception text from httpx can include the token-bearing URL, so it is never propagated.
        try:
            response = self._http_client.post(
                self._api_url,
                params={"token": self._token},
                json={operation: payload},
                headers={"Content-Type": "application/json"},
            )
        except httpx.RequestError:
            raise TelcovisionError("transport") from None

        if not response.is_success:
            raise TelcovisionError("http_status")

        try:
            body = response.json()
        except ValueError:
            raise TelcovisionError("invalid_json") from None
        if not isinstance(body, dict):
            raise TelcovisionError("invalid_response")

        status = body.get("status")
        code = status.get("code") if isinstance(status, dict) else None
        if isinstance(code, bool) or not isinstance(code, int | float):
            raise TelcovisionError("invalid_response")
        if code != 0:
            raise TelcovisionError("provider_status", int(code))
        return body

    def list_reseller_accounts(self) -> dict[str, object]:
        return self._request("listResellerAccount", {})

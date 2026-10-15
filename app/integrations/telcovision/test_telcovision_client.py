import logging

import httpx
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.config import Settings
from app.integrations.telcovision import cache as cache_module
from app.integrations.telcovision.accounts import parse_account_snapshot
from app.integrations.telcovision.cache import TelcovisionCache
from app.integrations.telcovision.client import TelcovisionClient, TelcovisionError

API_URL = "https://ocs.example.com/api/v1"
TOKEN = "super-secret-token"
OK_BODY = {
    "status": {"code": 0},
    "listResellerAccount": {
        "reseller": [
            {
                "id": 1,
                "account": [
                    {"id": 10, "name": "Acme Marine", "balance": 123.45, "packageOnly": False}
                ],
            }
        ]
    },
}


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}
        self.fail = False

    def _check(self) -> None:
        if self.fail:
            raise RedisConnectionError("down")

    def get(self, key):
        self._check()
        return self.store.get(key)

    def set(self, key, value, nx=False, ex=None):
        self._check()
        if nx and key in self.store:
            return None
        self.store[key] = value.encode() if isinstance(value, str) else value
        if ex:
            self.ttls[key] = ex
        return True

    def delete(self, key):
        self._check()
        self.store.pop(key, None)
        self.ttls.pop(key, None)


def make_settings(**overrides) -> Settings:
    values = {
        "REDIS_HOST": "redis",
        "TELCOVISION_API_URL": API_URL,
        "TELCOVISION_API_TOKEN": TOKEN,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def redis_fake(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache_module, "get_sync_redis", lambda settings: fake)
    cache_module._warned_reasons.clear()
    return fake


def build_client(handler, cache=None) -> TelcovisionClient:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return TelcovisionClient(API_URL, TOKEN, http, cache, request_id="req-1")


def counting_handler(calls: list, response: httpx.Response | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return response or httpx.Response(200, json=OK_BODY)

    return handler


def cache_for(redis_fake, **overrides) -> TelcovisionCache:
    cache = TelcovisionCache.from_settings(make_settings(**overrides), scope=API_URL)
    assert cache is not None
    return cache


def test_second_call_is_served_from_cache(redis_fake) -> None:
    calls: list = []
    client = build_client(counting_handler(calls), cache_for(redis_fake))

    first = client.list_reseller_accounts(validate=parse_account_snapshot)
    second = client.list_reseller_accounts(validate=parse_account_snapshot)

    assert first == second == OK_BODY
    assert len(calls) == 1
    (ttl,) = redis_fake.ttls.values()
    assert ttl == 60


def test_force_bypasses_read_but_refreshes_entry(redis_fake) -> None:
    calls: list = []
    client = build_client(counting_handler(calls), cache_for(redis_fake))

    client.list_reseller_accounts()
    client.list_reseller_accounts(bypass_cache=True)
    client.list_reseller_accounts()

    assert len(calls) == 2


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, text="boom"),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"status": {"code": 7}}),
        httpx.Response(200, json={"status": {"code": 0}, "unexpected": True}),
    ],
)
def test_failures_are_not_cached(redis_fake, response) -> None:
    calls: list = []
    client = build_client(counting_handler(calls, response), cache_for(redis_fake))

    for _ in range(2):
        with pytest.raises(TelcovisionError):
            client.list_reseller_accounts(validate=parse_account_snapshot)

    assert len(calls) == 2
    assert not redis_fake.ttls


def test_tampered_entry_is_evicted_and_refetched(redis_fake) -> None:
    calls: list = []
    client = build_client(counting_handler(calls), cache_for(redis_fake))
    client.list_reseller_accounts()
    (key,) = redis_fake.ttls
    redis_fake.store[key] = b"garbage"

    assert client.list_reseller_accounts() == OK_BODY
    assert len(calls) == 2
    assert redis_fake.store[key] != b"garbage"


def test_invalid_cached_shape_is_evicted(redis_fake) -> None:
    calls: list = []
    cache = cache_for(redis_fake)
    cache._write(cache._key("listResellerAccount", {}), {"status": {"code": 0}, "bad": 1}, "setup")
    client = build_client(counting_handler(calls), cache)

    assert client.list_reseller_accounts(validate=parse_account_snapshot) == OK_BODY
    assert len(calls) == 1


def test_redis_outage_falls_back_to_live_call(redis_fake) -> None:
    calls: list = []
    client = build_client(counting_handler(calls), cache_for(redis_fake))
    redis_fake.fail = True

    assert client.list_reseller_accounts() == OK_BODY
    assert client.list_reseller_accounts() == OK_BODY
    assert len(calls) == 2


@pytest.mark.parametrize(
    "overrides",
    [
        {"TELCOVISION_CACHE_ENABLED": "false"},
        {"REDIS_HOST": ""},
    ],
)
def test_cache_is_disabled_when_switched_off_or_without_redis(
    redis_fake, monkeypatch, overrides
) -> None:
    if "REDIS_HOST" in overrides:
        monkeypatch.setattr(cache_module, "get_sync_redis", lambda settings: None)
    assert TelcovisionCache.from_settings(make_settings(**overrides), scope=API_URL) is None
    assert not redis_fake.store


def test_different_endpoints_do_not_share_entries(redis_fake) -> None:
    settings = make_settings()
    a = TelcovisionCache.from_settings(settings, scope="https://a.example.com")
    b = TelcovisionCache.from_settings(settings, scope="https://b.example.com")
    assert a._key("op", {}) != b._key("op", {})


def test_transport_error_is_logged_without_token(caplog) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    with caplog.at_level(logging.INFO), pytest.raises(TelcovisionError) as caught:
        build_client(handler).list_reseller_accounts()

    assert caught.value.category == "transport"
    assert "category=transport" in caplog.text
    assert "error=ConnectTimeout" in caplog.text
    assert "request_id=req-1" in caplog.text
    assert TOKEN not in caplog.text and "token=" not in caplog.text


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (httpx.Response(503, text="down"), "http_status=503"),
        (httpx.Response(200, text="<html>"), "category=invalid_json"),
        (httpx.Response(200, json={"status": {"code": 9}}), "provider_code=9"),
    ],
)
def test_failure_categories_are_logged(response, expected, caplog) -> None:
    with caplog.at_level(logging.INFO), pytest.raises(TelcovisionError):
        build_client(counting_handler([], response)).list_reseller_accounts()

    assert expected in caplog.text
    assert "duration_ms=" in caplog.text
    assert TOKEN not in caplog.text


def test_success_and_cache_events_are_logged_without_data(redis_fake, caplog) -> None:
    client = build_client(counting_handler([]), cache_for(redis_fake))
    with caplog.at_level(logging.INFO):
        client.list_reseller_accounts()
        client.list_reseller_accounts()

    for event in ("request started", "request succeeded", "cache miss", "cache hit"):
        assert f"Telcovision {event}" in caplog.text
    assert "target=ocs.example.com/api/v1" in caplog.text
    assert "Acme Marine" not in caplog.text and TOKEN not in caplog.text
    assert "super-secret" not in caplog.text


def test_validation_failure_log_omits_provider_values(caplog) -> None:
    body = {"status": {"code": 0}, "listResellerAccount": {"reseller": [{"id": "SECRETVALUE"}]}}
    with caplog.at_level(logging.INFO), pytest.raises(TelcovisionError):
        build_client(counting_handler([], httpx.Response(200, json=body))).list_reseller_accounts(
            validate=parse_account_snapshot
        )
    assert "category=invalid_response" in caplog.text
    assert "SECRETVALUE" not in caplog.text

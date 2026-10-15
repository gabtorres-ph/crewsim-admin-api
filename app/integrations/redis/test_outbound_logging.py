import json
from typing import Any

import pytest

from app.config import Settings
from app.integrations.redis import outbound_logging
from app.integrations.redis.request_logging import MAX_BODY_BYTES, RequestLogManager, outbound_key
from app.integrations.redis.test_request_logging import _FakeRedis


class _SyncRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value
        if ex:
            self.ttls[key] = ex


@pytest.fixture
def sync_redis(monkeypatch: pytest.MonkeyPatch) -> _SyncRedis:
    fake = _SyncRedis()
    monkeypatch.setattr(RequestLogManager, "is_enabled", classmethod(lambda cls: True))
    monkeypatch.setattr(outbound_logging, "get_sync_redis", lambda settings: fake)
    return fake


SETTINGS = Settings(_env_file=None, REDIS_HOST="redis")


def _call(**overrides: Any) -> dict[str, Any]:
    call = {
        "operation": "listResellerAccount",
        "target": "ocs.example.com/api/v1",
        "source": "live",
        "outcome": "ok",
        "at": "2026-01-01T00:00:00+00:00",
        "http_status": 200,
        "content_type": "application/json",
        "bytes": 40,
        "duration_ms": 120,
        "body_text": json.dumps({"status": {"code": 0}, "name": "Acme Marine", "balance": 1.5}),
    }
    call.update(overrides)
    return call


def test_calls_are_stored_under_the_request_with_retention(sync_redis: _SyncRedis) -> None:
    outbound_logging.write_outbound_calls(SETTINGS, "abc", [_call()])

    stored = json.loads(sync_redis.values[outbound_key("abc")])
    assert sync_redis.ttls[outbound_key("abc")] == 259200
    assert stored[0]["body"]["name"] == "Acme Marine"  # business data is logged for now
    assert stored[0]["body_truncated"] is False
    assert "body_text" not in stored[0]
    assert stored[0]["http_status"] == 200 and stored[0]["source"] == "live"


def test_secret_keys_are_redacted_and_large_bodies_truncated(sync_redis: _SyncRedis) -> None:
    secret = json.dumps({"token": "abc123", "pad": "x" * (MAX_BODY_BYTES * 2)})
    outbound_logging.write_outbound_calls(SETTINGS, "abc", [_call(body_text=secret)])

    stored = json.loads(sync_redis.values[outbound_key("abc")])[0]
    assert "abc123" not in json.dumps(stored)
    assert stored["body_truncated"] is True


def test_no_write_when_request_logging_is_disabled(
    sync_redis: _SyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(RequestLogManager, "is_enabled", classmethod(lambda cls: False))
    outbound_logging.write_outbound_calls(SETTINGS, "abc", [_call()])
    assert not sync_redis.values


def test_write_failure_never_raises(
    sync_redis: _SyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    from redis.exceptions import ConnectionError as RedisConnectionError

    def boom(*args: Any, **kwargs: Any) -> None:
        raise RedisConnectionError("down")

    monkeypatch.setattr(sync_redis, "set", boom)
    outbound_logging.write_outbound_calls(SETTINGS, "abc", [_call()])


@pytest.mark.asyncio
async def test_entries_expose_outbound_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata = {b"ts": b"1", b"status": b"200", b"duration_ms": b"5"}
    outbound = json.dumps([{"operation": "listResellerAccount", "outcome": "ok"}]).encode()
    client = _FakeRedis([metadata, b"{}", b"{}", outbound])
    monkeypatch.setattr(RequestLogManager, "_client", client)
    monkeypatch.setattr(RequestLogManager, "_enabled", True)

    (entry,) = await RequestLogManager._build_entries(["abc"], include_body=True)

    assert entry["outbound"] == [{"operation": "listResellerAccount", "outcome": "ok"}]


@pytest.mark.asyncio
async def test_deleting_a_request_removes_its_outbound_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeRedis([])
    monkeypatch.setattr(RequestLogManager, "_client", client)
    monkeypatch.setattr(RequestLogManager, "_enabled", True)

    await RequestLogManager._delete_request_data(["abc"])

    deleted = {key for name, args in client.pipelines[0].calls if name == "delete" for key in args}
    assert outbound_key("abc") in deleted


@pytest.mark.asyncio
async def test_refresh_route_passes_the_inbound_request_id(client, monkeypatch) -> None:
    from app.accounts import routes
    from app.accounts.schemas import AccountRefreshResult

    seen: dict[str, Any] = {}

    def fake_refresh(db, settings, *, force, request_id):
        seen.update(force=force, request_id=request_id)
        return AccountRefreshResult(
            fetched=0, created=0, updated=0, unchanged=0, deleted=0, delinked_esims=0
        )

    monkeypatch.setattr(routes, "refresh_telcovision_accounts", fake_refresh)
    response = await client.post("/api/accounts/refresh?force=true")

    assert response.status_code == 200
    assert seen["force"] is True
    assert len(seen["request_id"]) == 32  # the middleware's UUID, not a locally generated ID

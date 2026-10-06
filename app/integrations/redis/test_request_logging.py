import gzip
import json
from typing import Any

import pytest
from starlette.requests import Request

from app.integrations.redis import request_logging_middleware
from app.integrations.redis.request_logging import (
    MAX_BODY_BYTES,
    MAX_CAPTURE_BYTES,
    RequestBodySnapshot,
    RequestLogManager,
)


def _stored(snapshot: RequestBodySnapshot) -> str:
    body = gzip.decompress(snapshot.stored_body) if snapshot.gzip else snapshot.stored_body
    return body.decode("utf-8")


def _make_request(path: str = "/api/auth/login", method: str = "POST") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "client": ("203.0.113.1", 1234),
            "server": ("testserver", 80),
        }
    )


class _FakePipeline:
    def __init__(self, results: list[Any]) -> None:
        self.results = results
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def __aenter__(self) -> "_FakePipeline":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def __getattr__(self, name: str) -> Any:
        def record(*args: Any, **kwargs: Any) -> None:
            self.calls.append((name, args))

        return record

    async def execute(self) -> list[Any]:
        return self.results


class _FakeRedis:
    def __init__(self, results: list[Any]) -> None:
        self.results = results
        self.pipelines: list[_FakePipeline] = []

    def pipeline(self, transaction: bool = True) -> _FakePipeline:
        pipeline = _FakePipeline(self.results)
        self.pipelines.append(pipeline)
        return pipeline

    def scan_iter(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("user indexes must not be scanned")


@pytest.fixture
def scheduled(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    monkeypatch.setattr(RequestLogManager, "is_enabled", classmethod(lambda cls: True))
    monkeypatch.setattr(
        RequestLogManager, "schedule_log", classmethod(lambda cls, **data: logs.append(data))
    )
    return logs


@pytest.mark.asyncio
async def test_streamed_json_over_storage_cap_is_redacted_before_truncation(
    scheduled: list[dict[str, Any]],
) -> None:
    payload = json.dumps({"access_token": "s3cret-token", "items": ["x" * 100] * 500})
    assert MAX_BODY_BYTES < len(payload) < MAX_CAPTURE_BYTES

    async def chunks():
        for offset in range(0, len(payload), 4096):
            yield payload[offset : offset + 4096].encode("utf-8")

    stream = request_logging_middleware._capture_stream(
        chunks(),
        request=_make_request(),
        request_id="abc",
        ts_ms=0,
        body_snapshot=None,
        status=200,
        content_type="application/json",
        charset="utf-8",
        started_at=0.0,
    )
    async for _ in stream:
        pass

    snapshot = scheduled[0]["response_body_snapshot"]
    stored = _stored(snapshot)
    assert snapshot.truncated
    assert "s3cret-token" not in stored
    assert '"access_token":"[REDACTED]"' in stored


def test_stream_longer_than_capture_limit_is_omitted() -> None:
    body = b'{"password":"hunter2",' + b" " * 100
    snapshot = RequestLogManager.capture_response_body(
        body, "application/json", raw_length=MAX_CAPTURE_BYTES + 1
    )

    assert json.loads(_stored(snapshot))["reason"] == "too_large"


def test_malformed_json_is_omitted_instead_of_stored_raw() -> None:
    snapshot = RequestLogManager.capture_response_body(
        b'{"email":"a@b.c","password":"hunter2",}', "application/json"
    )

    stored = _stored(snapshot)
    assert "hunter2" not in stored
    assert json.loads(stored)["reason"] == "unparseable_json"


def test_empty_json_body_is_stored_empty() -> None:
    snapshot = RequestLogManager.capture_response_body(b"", "application/json")

    assert snapshot.stored_body == b""


@pytest.mark.parametrize("content_type", ["text/plain", "application/json"])
def test_deeply_nested_body_does_not_raise(content_type: str) -> None:
    snapshot = RequestLogManager.capture_response_body(b"[" * 100_000, content_type)

    assert json.loads(_stored(snapshot))["reason"] == "unparseable_json"


def test_capture_failure_is_stored_as_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(cls: type, body: bytes, content_type: str) -> bytes:
        raise RuntimeError("boom")

    monkeypatch.setattr(RequestLogManager, "_redact_body", classmethod(fail))

    snapshot = RequestLogManager.capture_response_body(b"{}", "application/json")

    assert json.loads(_stored(snapshot))["reason"] == "capture_failed"


def test_unmatched_route_uses_fixed_metrics_path(scheduled: list[dict[str, Any]]) -> None:
    request = _make_request("/wp-admin/" + "a" * 500, method="GET")

    request_logging_middleware._schedule_log(
        request, request_id="abc", ts_ms=0, body_snapshot=None, status=404, started_at=0.0
    )

    assert scheduled[0]["metrics_path"] == "__unmatched__"
    assert scheduled[0]["path"] == ("/wp-admin/" + "a" * 500)[:256]


@pytest.mark.asyncio
async def test_unknown_method_is_grouped_in_metrics_key(monkeypatch: pytest.MonkeyPatch) -> None:
    results: list[Any] = [None] * 13
    results[10], results[11] = 1, 5.0
    client = _FakeRedis(results)
    monkeypatch.setattr(RequestLogManager, "_client", client)
    monkeypatch.setattr(RequestLogManager, "_enabled", True)

    async def no_purge(cls: type, *args: Any, **kwargs: Any) -> int:
        return 0

    monkeypatch.setattr(RequestLogManager, "purge_expired_logs", classmethod(no_purge))

    await RequestLogManager.log_request(
        request_id="abc",
        ts_ms=0,
        caller_ip="203.0.113.1",
        user_id="anonymous",
        method="FOOBAR",
        path="/random",
        metrics_path="__unmatched__",
        status=404,
        duration_ms=5.0,
    )

    keys = {args[0] for name, args in client.pipelines[0].calls if name == "hincrby"}
    assert keys == {"req:metrics:OTHER:__unmatched__"}


@pytest.mark.asyncio
async def test_missing_request_id_does_not_scan_or_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeRedis([{}, None, None])
    monkeypatch.setattr(RequestLogManager, "_client", client)
    monkeypatch.setattr(RequestLogManager, "_enabled", True)

    assert await RequestLogManager.get_request_by_id("missing") is None
    assert len(client.pipelines) == 1


@pytest.mark.asyncio
async def test_orphan_from_user_index_is_removed_from_that_index_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeRedis([{}])
    monkeypatch.setattr(RequestLogManager, "_client", client)
    monkeypatch.setattr(RequestLogManager, "_enabled", True)

    await RequestLogManager._build_entries(
        [b"gone"], include_body=False, index_key="user:7:reqs"
    )

    repair = client.pipelines[1].calls
    assert ("zrem", ("req:all", "gone")) in repair
    assert ("zrem", ("user:7:reqs", "gone")) in repair

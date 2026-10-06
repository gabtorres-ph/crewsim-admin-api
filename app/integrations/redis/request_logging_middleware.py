"""Capture request and response logs without waiting for Redis writes."""

import codecs
import re
import time
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any
from uuid import uuid4

from fastapi import Request, Response
from starlette.concurrency import iterate_in_threadpool
from starlette.middleware.base import RequestResponseEndpoint

from app.integrations.redis.request_logging import (
    MAX_BODY_BYTES,
    RequestBodySnapshot,
    RequestLogManager,
)


def _resolved_path(request: Request) -> str:
    """Use the route matched during dispatch, or the unmodified URL path."""
    route_path = getattr(request.scope.get("route"), "path", None)
    if not route_path:
        return request.url.path
    return re.sub(r"\{([^{}:]+)(?::[^{}]+)?\}", r":\1", route_path)


def _schedule_log(
    request: Request,
    *,
    request_id: str,
    ts_ms: int,
    body_snapshot: RequestBodySnapshot | None,
    status: int,
    started_at: float,
    response_body_snapshot: RequestBodySnapshot | None = None,
) -> None:
    if status == 307 or not RequestLogManager.is_enabled():
        return

    user_id = getattr(request.state, "user_id", None)
    RequestLogManager.schedule_log(
        request_id=request_id,
        ts_ms=ts_ms,
        caller_ip=request.client.host if request.client else "anonymous",
        user_id=str(user_id) if user_id else "anonymous",
        method=request.method,
        path=_resolved_path(request),
        status=status,
        duration_ms=(time.perf_counter() - started_at) * 1000,
        body_snapshot=body_snapshot,
        response_body_snapshot=response_body_snapshot,
    )


async def _capture_stream(
    body_iterator: Any,
    *,
    request: Request,
    request_id: str,
    ts_ms: int,
    body_snapshot: RequestBodySnapshot | None,
    status: int,
    content_type: str,
    charset: str,
    started_at: float,
) -> AsyncIterator[Any]:
    captured = bytearray()
    total_length = 0
    omit_body = RequestLogManager._is_omitted_content_type(content_type)
    chunks = (
        body_iterator
        if isinstance(body_iterator, AsyncIterable)
        else iterate_in_threadpool(body_iterator)
    )

    def record_body(body: bytes | memoryview) -> None:
        nonlocal total_length
        view = memoryview(body).cast("B")
        total_length += len(view)
        remaining = MAX_BODY_BYTES - len(captured)
        if not omit_body and remaining > 0:
            captured.extend(view[:remaining])

    try:
        async for chunk in chunks:
            # Starlette encodes string chunks when sending them. Preserve the
            # original chunk and encode in pieces to bound capture memory.
            if isinstance(chunk, str):
                encoder = codecs.getincrementalencoder(charset)()
                for offset in range(0, len(chunk), 4096):
                    record_body(encoder.encode(chunk[offset : offset + 4096]))
                record_body(encoder.encode("", final=True))
            elif isinstance(chunk, bytes | memoryview):
                record_body(chunk)
            else:
                # Starlette may yield an ASGI pathsend message for a file.
                yield chunk
                continue
            yield chunk
    finally:
        snapshot = RequestLogManager.capture_response_body(
            bytes(captured), content_type, raw_length=total_length
        )
        _schedule_log(
            request,
            request_id=request_id,
            ts_ms=ts_ms,
            body_snapshot=body_snapshot,
            response_body_snapshot=snapshot,
            status=status,
            started_at=started_at,
        )


async def handle_request_logging(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Assign a request ID and capture eligible request and response bodies."""
    request_id = uuid4().hex
    request.state.request_id = request_id
    ts_ms = int(time.time() * 1000)

    enabled = RequestLogManager.is_enabled()
    body_snapshot = await RequestLogManager.capture_body(request) if enabled else None
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        _schedule_log(
            request,
            request_id=request_id,
            ts_ms=ts_ms,
            body_snapshot=body_snapshot,
            status=500,
            started_at=started_at,
        )
        raise

    if not enabled or response.status_code == 307:
        return response

    content_type = response.headers.get("content-type", "")
    buffered_body = getattr(response, "body", None)
    if buffered_body is not None:
        snapshot = RequestLogManager.capture_response_body(buffered_body, content_type)
        _schedule_log(
            request,
            request_id=request_id,
            ts_ms=ts_ms,
            body_snapshot=body_snapshot,
            response_body_snapshot=snapshot,
            status=response.status_code,
            started_at=started_at,
        )
    elif (body_iterator := getattr(response, "body_iterator", None)) is not None:
        response.body_iterator = _capture_stream(
            body_iterator,
            request=request,
            request_id=request_id,
            ts_ms=ts_ms,
            body_snapshot=body_snapshot,
            status=response.status_code,
            content_type=content_type,
            charset=response.charset,
            started_at=started_at,
        )
    else:
        _schedule_log(
            request,
            request_id=request_id,
            ts_ms=ts_ms,
            body_snapshot=body_snapshot,
            status=response.status_code,
            started_at=started_at,
        )

    return response

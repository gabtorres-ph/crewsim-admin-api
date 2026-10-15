"""HTTPX helpers that capture sanitized outbound exchanges for inspection."""

import logging
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from app.integrations.redis.outbound_logging import (
    OutboundExchange,
    sanitize_outbound_body,
    sanitize_outbound_headers,
    sanitize_outbound_url,
)

logger = logging.getLogger(__name__)


def _body_content(message: httpx.Request | httpx.Response) -> bytes | None:
    try:
        return message.content
    except (httpx.RequestNotRead, httpx.ResponseNotRead):
        return None


def _capture_exchange(
    *,
    request: httpx.Request,
    response: httpx.Response | None,
    request_id: str,
    operation: str,
    exchanges: list[OutboundExchange],
    started_at: float,
    error_category: str | None,
) -> None:
    try:
        target, query = sanitize_outbound_url(str(request.url))
        request_body, request_bytes, request_omitted = sanitize_outbound_body(
            _body_content(request), request.headers.get("content-type", "")
        )
        response_body, response_bytes, response_omitted = (
            sanitize_outbound_body(
                _body_content(response), response.headers.get("content-type", "")
            )
            if response is not None
            else (None, 0, False)
        )
        outcome = (
            "transport_error"
            if error_category is not None
            else "ok" if response is not None and response.is_success else "http_error"
        )
        exchanges.append(
            OutboundExchange(
                request_id=request_id,
                operation=operation,
                at=datetime.now(UTC).isoformat(),
                method=request.method,
                target=target,
                query=query,
                request_headers=sanitize_outbound_headers(request.headers),
                request_body=request_body,
                request_body_bytes=request_bytes,
                request_body_omitted=request_omitted,
                response_status=response.status_code if response is not None else None,
                response_headers=(
                    sanitize_outbound_headers(response.headers) if response is not None else {}
                ),
                response_body=response_body,
                response_body_bytes=response_bytes,
                response_body_omitted=response_omitted,
                duration_ms=(time.perf_counter() - started_at) * 1000,
                outcome=outcome,
                error_category=error_category,
            )
        )
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        logger.warning("Outbound exchange capture failed error=%s", type(error).__name__)


def logged_request(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    operation: str,
    request_id: str,
    exchanges: list[OutboundExchange],
    **kwargs: Any,
) -> httpx.Response:
    """Send a synchronous HTTP request and append its sanitized network result."""
    request = client.build_request(method, url, **kwargs)
    response: httpx.Response | None = None
    error_category: str | None = None
    started_at = time.perf_counter()
    try:
        response = client.send(request)
        return response
    except httpx.RequestError as error:
        error_category = type(error).__name__
        raise
    finally:
        _capture_exchange(
            request=request,
            response=response,
            request_id=request_id,
            operation=operation,
            exchanges=exchanges,
            started_at=started_at,
            error_category=error_category,
        )


async def logged_async_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    operation: str,
    request_id: str,
    exchanges: list[OutboundExchange],
    **kwargs: Any,
) -> httpx.Response:
    """Send an asynchronous HTTP request and append its sanitized network result."""
    request = client.build_request(method, url, **kwargs)
    response: httpx.Response | None = None
    error_category: str | None = None
    started_at = time.perf_counter()
    try:
        response = await client.send(request)
        return response
    except httpx.RequestError as error:
        error_category = type(error).__name__
        raise
    finally:
        _capture_exchange(
            request=request,
            response=response,
            request_id=request_id,
            operation=operation,
            exchanges=exchanges,
            started_at=started_at,
            error_category=error_category,
        )

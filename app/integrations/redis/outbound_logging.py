"""Attach outbound provider calls to the request-log entry of the request that caused them."""

import json
import logging
from typing import Any

from redis.exceptions import RedisError

from app.config import Settings
from app.integrations.redis.request_logging import (
    REQUEST_LOG_TTL_SECONDS,
    RequestLogManager,
    outbound_key,
)
from app.integrations.redis.sync_client import get_sync_redis

logger = logging.getLogger(__name__)


def _to_entry(call: dict[str, Any]) -> dict[str, Any]:
    entry = {key: value for key, value in call.items() if key != "body_text"}
    body_text = call.get("body_text")
    if isinstance(body_text, str):
        # Same redaction and size cap as captured request and response bodies.
        entry["body"], entry["body_truncated"] = RequestLogManager.sanitize_for_log(
            body_text.encode("utf-8"), str(call.get("content_type") or "application/json")
        )
    return entry


def write_outbound_calls(settings: Settings, request_id: str, calls: list[dict[str, Any]]) -> None:
    """Persist outbound call records; never raises, because logging must not fail the request."""
    if not calls or not RequestLogManager.is_enabled():
        return
    client = get_sync_redis(settings)
    if client is None:
        return
    try:
        payload = json.dumps([_to_entry(call) for call in calls], default=str)
        client.set(outbound_key(request_id), payload, ex=REQUEST_LOG_TTL_SECONDS)
    except (RedisError, TypeError, ValueError) as error:
        logger.warning(
            "Outbound request logging failed request_id=%s error=%s",
            request_id,
            type(error).__name__,
        )

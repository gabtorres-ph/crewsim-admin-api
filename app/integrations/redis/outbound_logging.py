"""Safe, short-lived records of outbound HTTP exchanges."""

import re
from collections.abc import Mapping
from typing import Any, TypedDict
from urllib.parse import parse_qs, parse_qsl, urlsplit

from app.integrations.redis.request_logging import REDACTED_VALUE, SENSITIVE_KEY_PARTS

MAX_OUTBOUND_BODY_BYTES = 5 * 1024 * 1024
SAFE_HEADER_NAMES = frozenset({"accept", "content-type", "content-length"})
SENSITIVE_OUTBOUND_KEY_PARTS = (*SENSITIVE_KEY_PARTS, "auth", "credential", "signature", "key")


class OutboundExchange(TypedDict):
    """A sanitized HTTP attempt associated with an inbound request ID."""

    request_id: str
    operation: str
    at: str
    method: str
    target: str
    query: list[dict[str, str]]
    request_headers: dict[str, str]
    request_body: Any
    request_body_bytes: int
    request_body_omitted: bool
    response_status: int | None
    response_headers: dict[str, str]
    response_body: Any
    response_body_bytes: int
    response_body_omitted: bool
    duration_ms: float
    outcome: str
    error_category: str | None


def _is_sensitive(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    return any(part in normalized for part in SENSITIVE_OUTBOUND_KEY_PARTS)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: REDACTED_VALUE if _is_sensitive(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def sanitize_outbound_url(url: str) -> tuple[str, list[dict[str, str]]]:
    """Keep the destination and query structure without URL credentials or fragments."""
    parts = urlsplit(url)
    host = parts.hostname or "unknown"
    if ":" in host:
        host = f"[{host}]"
    port = f":{parts.port}" if parts.port is not None else ""
    target = f"{parts.scheme}://{host}{port}{parts.path or '/'}"
    query = [
        {"name": name, "value": REDACTED_VALUE if _is_sensitive(name) else value}
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return target, query


def sanitize_outbound_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Store only non-credential headers useful for interpreting an exchange."""
    return {
        name.lower(): value
        for name, value in headers.items()
        if name.lower() in SAFE_HEADER_NAMES
    }


def _omitted_body(reason: str, content_type: str, length: int) -> dict[str, Any]:
    return {
        "omitted": True,
        "reason": reason,
        "content_type": content_type,
        "content_length": length,
    }


def sanitize_outbound_body(body: bytes | None, content_type: str) -> tuple[Any, int, bool]:
    """Redact a complete structured body, or return an explicit omission marker."""
    if body is None:
        return _omitted_body("unreadable", content_type, 0), 0, True
    length = len(body)
    if not body:
        return None, 0, False
    if length > MAX_OUTBOUND_BODY_BYTES:
        return _omitted_body("too_large", content_type, length), length, True

    base_type = content_type.split(";", 1)[0].strip().lower()
    try:
        decoded = body.decode("utf-8")
        if "json" in base_type or decoded.lstrip().startswith(("{", "[")):
            value = json.loads(decoded)
        elif base_type == "application/x-www-form-urlencoded":
            value = {
                name: values[0] if len(values) == 1 else values
                for name, values in parse_qs(decoded, keep_blank_values=True).items()
            }
        else:
            return _omitted_body("unsupported_content_type", content_type, length), length, True
        safe_value = _redact(value)
        if len(json.dumps(safe_value, ensure_ascii=True).encode("utf-8")) > MAX_OUTBOUND_BODY_BYTES:
            return _omitted_body("too_large", content_type, length), length, True
        return safe_value, length, False
    except (UnicodeDecodeError, ValueError, TypeError, RecursionError):
        return _omitted_body("unparseable", content_type, length), length, True

"""Redis lifecycle and safe body capture for request logging."""

import asyncio
import gzip
import json
import logging
import re
import zlib
from dataclasses import dataclass
from typing import Any, ClassVar
from urllib.parse import parse_qs

from fastapi import Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

REQUEST_LOG_TTL_SECONDS = 259200
REQUEST_LOG_PURGE_INTERVAL_SECONDS = 60
REQUEST_LOG_PURGE_BATCH_SIZE = 500
REQUEST_LOG_SHUTDOWN_TIMEOUT_SECONDS = 5
MAX_BODY_BYTES = 32 * 1024
COMPRESS_THRESHOLD_BYTES = 1024
REDACTED_VALUE = "[REDACTED]"
SENSITIVE_KEY_PARTS = (
    "password", "passwd", "pwd", "token", "authorization", "cookie", "secret", "apikey"
)


@dataclass
class RequestBodySnapshot:
    content_type: str
    raw_length: int
    stored_body: bytes
    truncated: bool
    gzip: bool


class RequestLogManager:
    """Own the Redis client and background tasks for the application lifespan."""

    _client: ClassVar[Redis | None] = None
    _enabled: ClassVar[bool] = False
    _last_purge_monotonic: ClassVar[float] = 0.0
    _purge_lock: ClassVar[asyncio.Lock | None] = None
    _cleanup_task: ClassVar[asyncio.Task[None] | None] = None
    _write_tasks: ClassVar[set[asyncio.Task[None]]] = set()

    @staticmethod
    def _normalize_content_type(content_type: str) -> str:
        return content_type.split(";", 1)[0].strip().lower()

    @classmethod
    def _is_omitted_content_type(cls, content_type: str) -> bool:
        base_type = cls._normalize_content_type(content_type)
        textual = (
            not base_type
            or base_type.startswith("text/")
            or "json" in base_type
            or base_type in {
                "application/x-www-form-urlencoded", "application/xml", "application/graphql"
            }
        )
        return (
            base_type.startswith(("multipart/", "image/", "audio/", "video/"))
            or base_type in {
                "application/octet-stream", "application/pdf", "application/zip",
                "application/x-zip-compressed",
            }
            or (base_type.startswith("application/") and not textual)
        )

    @classmethod
    def _redact_sensitive_values(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: (
                    REDACTED_VALUE
                    if any(
                        part in re.sub(r"[^a-z0-9]", "", str(key).lower())
                        for part in SENSITIVE_KEY_PARTS
                    )
                    else cls._redact_sensitive_values(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [cls._redact_sensitive_values(item) for item in value]
        return value

    @classmethod
    def _redact_body(cls, body: bytes, content_type: str) -> bytes:
        base_type = cls._normalize_content_type(content_type)
        decoded = body.decode("utf-8", errors="replace")
        if "json" in base_type or decoded.lstrip().startswith(("{", "[")):
            try:
                value = json.loads(decoded)
            except ValueError:
                return decoded.encode("utf-8")
        elif base_type == "application/x-www-form-urlencoded":
            value = {
                key: values[0] if len(values) == 1 else values
                for key, values in parse_qs(decoded, keep_blank_values=True).items()
            }
        else:
            return decoded.encode("utf-8")
        return json.dumps(
            cls._redact_sensitive_values(value), separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")

    @classmethod
    async def capture_body(cls, request: Request) -> RequestBodySnapshot:
        """Read textual bodies through Starlette's cache; never read omitted bodies."""
        content_type = request.headers.get("content-type", "")
        if cls._is_omitted_content_type(content_type):
            try:
                raw_length = max(0, int(request.headers.get("content-length", "0")))
            except ValueError:
                raw_length = 0
            return cls.capture_response_body(b"", content_type, raw_length=raw_length)
        return cls.capture_response_body(await request.body(), content_type)

    @classmethod
    def capture_response_body(
        cls, body: bytes, content_type: str, *, raw_length: int | None = None
    ) -> RequestBodySnapshot:
        """Sanitize before applying the storage cap and optional compression."""
        length = len(body) if raw_length is None else raw_length
        if cls._is_omitted_content_type(content_type):
            stored_body = json.dumps(
                {
                    "omitted": True,
                    "reason": "binary_or_multipart",
                    "content_type": content_type,
                    "content_length": length,
                },
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        else:
            stored_body = cls._redact_body(body, content_type)
        truncated = length > MAX_BODY_BYTES or len(stored_body) > MAX_BODY_BYTES
        stored_body = stored_body[:MAX_BODY_BYTES]
        gzip_encoded = len(stored_body) > COMPRESS_THRESHOLD_BYTES
        if gzip_encoded:
            stored_body = gzip.compress(stored_body)
        return RequestBodySnapshot(content_type, length, stored_body, truncated, gzip_encoded)

    @classmethod
    def _decode_stored_body(cls, body: bytes, *, gzip_encoded: bool) -> Any:
        """Decode stored JSON or text, tolerating damaged gzip and truncated JSON."""
        if gzip_encoded:
            try:
                body = gzip.decompress(body)
            except (OSError, EOFError, zlib.error):
                pass
        decoded = body.decode("utf-8", errors="replace")
        try:
            return json.loads(decoded)
        except ValueError:
            return decoded

    @classmethod
    def init(
        cls,
        host: str,
        port: int = 6379,
        *,
        username: str = "",
        password: str = "",
    ) -> None:
        """Configure Redis without connecting or blocking application startup."""
        if cls._client is not None:
            logger.warning("Request logging is already initialized; close it before reinitializing")
            return

        cls._enabled = False
        if not host:
            return

        try:
            if not isinstance(host, str) or not isinstance(port, int) or not 1 <= port <= 65535:
                raise ValueError("Redis requires a string host and a port between 1 and 65535")
            cls._client = Redis(
                host=host,
                port=port,
                db=0,
                username=username or None,
                password=password or None,
                decode_responses=False,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
        except (RedisError, ValueError, TypeError) as error:
            logger.warning("Request logging Redis initialization failed: %s", error)
            cls._client = None
            return

        cls._enabled = True

    @classmethod
    def is_enabled(cls) -> bool:
        return cls._enabled and cls._client is not None

    @classmethod
    async def start_cleanup_task(cls) -> None:
        """Start a single periodic cleanup task when logging is configured."""
        if not cls.is_enabled():
            return
        if cls._cleanup_task is not None and not cls._cleanup_task.done():
            return
        cls._cleanup_task = asyncio.create_task(cls._cleanup_loop(), name="request-log-cleanup")

    @classmethod
    async def _cleanup_loop(cls) -> None:
        while True:
            await asyncio.sleep(REQUEST_LOG_PURGE_INTERVAL_SECONDS)
            try:
                await cls.purge_expired_logs(force=True)
            except RedisError as error:
                logger.warning("Request logging Redis cleanup failed: %s", error)

    @classmethod
    async def purge_expired_logs(cls, now_ms: int | None = None, *, force: bool = False) -> int:
        """Lifecycle hook; expiry and index repair are implemented in plan step 5."""
        return 0

    @classmethod
    async def close(cls) -> None:
        """Stop cleanup, drain writes for up to five seconds, and release Redis."""
        cls._enabled = False
        try:
            if cls._cleanup_task is not None:
                cls._cleanup_task.cancel()
                await asyncio.gather(cls._cleanup_task, return_exceptions=True)

            if cls._write_tasks:
                write_tasks = tuple(cls._write_tasks)
                _, pending = await asyncio.wait(
                    write_tasks, timeout=REQUEST_LOG_SHUTDOWN_TIMEOUT_SECONDS
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*write_tasks, return_exceptions=True)
        finally:
            try:
                if cls._client is not None:
                    await cls._client.aclose()
            except RedisError as error:
                logger.warning("Request logging Redis close failed: %s", error)
            finally:
                cls._client = None
                cls._enabled = False
                cls._last_purge_monotonic = 0.0
                cls._purge_lock = None
                cls._cleanup_task = None
                cls._write_tasks = set()

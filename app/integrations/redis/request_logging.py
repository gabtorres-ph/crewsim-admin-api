"""Redis lifecycle, safe body capture, and persistence for request logging."""

import asyncio
import gzip
import json
import logging
import re
import time
import zlib
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
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
# Streamed bodies are buffered up to this size so redaction sees complete JSON.
MAX_CAPTURE_BYTES = 256 * 1024
COMPRESS_THRESHOLD_BYTES = 1024
MAX_PATH_LENGTH = 256
UNMATCHED_PATH = "__unmatched__"
METRICS_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})
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

    @staticmethod
    def _omitted_body(reason: str, content_type: str, length: int) -> bytes:
        return json.dumps(
            {
                "omitted": True,
                "reason": reason,
                "content_type": content_type,
                "content_length": length,
            },
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

    @classmethod
    def _redact_body(cls, body: bytes, content_type: str) -> bytes | None:
        """Return the redacted body, or None when structured data cannot be redacted."""
        if not body:
            return b""
        base_type = cls._normalize_content_type(content_type)
        decoded = body.decode("utf-8", errors="replace")
        if "json" in base_type or decoded.lstrip().startswith(("{", "[")):
            try:
                value = json.loads(decoded)
            except (ValueError, RecursionError):
                return None
        elif base_type == "application/x-www-form-urlencoded":
            value = {
                key: values[0] if len(values) == 1 else values
                for key, values in parse_qs(decoded, keep_blank_values=True).items()
            }
        else:
            return decoded.encode("utf-8")
        try:
            return json.dumps(
                cls._redact_sensitive_values(value), separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
        except RecursionError:
            return None

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
        """Sanitize before applying the storage cap and optional compression.

        Bodies that cannot be redacted, including streams captured only in part, are
        replaced by a placeholder so unredacted secrets never reach Redis.
        """
        length = len(body) if raw_length is None else raw_length
        try:
            if cls._is_omitted_content_type(content_type):
                stored_body = cls._omitted_body("binary_or_multipart", content_type, length)
            elif length > len(body):
                stored_body = cls._omitted_body("too_large", content_type, length)
            else:
                redacted = cls._redact_body(body, content_type)
                stored_body = (
                    redacted
                    if redacted is not None
                    else cls._omitted_body("unparseable_json", content_type, length)
                )
        except Exception:
            # Logging must never fail the request it describes.
            logger.warning("Request logging body capture failed", exc_info=True)
            stored_body = cls._omitted_body("capture_failed", content_type, length)
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
    def schedule_log(cls, **log_data: Any) -> None:
        """Retain background writes until completion without waiting on Redis."""
        if not cls.is_enabled():
            return
        task = asyncio.create_task(cls.log_request(**log_data), name="request-log-write")
        cls._write_tasks.add(task)
        task.add_done_callback(cls._write_tasks.discard)

    @classmethod
    async def log_request(
        cls,
        *,
        request_id: str,
        ts_ms: int,
        caller_ip: str,
        user_id: str,
        method: str,
        path: str,
        metrics_path: str,
        status: int,
        duration_ms: float,
        body_snapshot: RequestBodySnapshot | None = None,
        response_body_snapshot: RequestBodySnapshot | None = None,
    ) -> None:
        """Persist a request and refresh every touched key's retention period.

        `metrics_path` must come from a bounded set (route templates) because it names a key.
        """
        client = cls._client
        if client is None:
            return
        try:
            await cls.purge_expired_logs()
            request_body = body_snapshot or RequestBodySnapshot("", 0, b"", False, False)
            response_body = response_body_snapshot or RequestBodySnapshot("", 0, b"", False, False)
            request_key = f"req:{request_id}"
            body_key = f"{request_key}:body"
            response_key = f"{request_key}:response_body"
            user_key = f"user:{user_id}:reqs"
            metrics_method = method if method in METRICS_METHODS else "OTHER"
            metrics_key = f"req:metrics:{metrics_method}:{metrics_path}"
            metadata = {
                "ts": str(ts_ms),
                "timestamp": datetime.fromtimestamp(ts_ms / 1000, tz=UTC).isoformat(),
                "caller_ip": caller_ip,
                "user_id": user_id,
                "method": method,
                "path": path,
                "status": str(status),
                "duration_ms": str(int(duration_ms)),
                "req_body_key": body_key,
                "req_body_len": str(request_body.raw_length),
                "req_body_truncated": str(int(request_body.truncated)),
                "req_body_gzip": str(int(request_body.gzip)),
                "content_type": request_body.content_type,
                "resp_body_key": response_key,
                "resp_body_len": str(response_body.raw_length),
                "resp_body_truncated": str(int(response_body.truncated)),
                "resp_body_gzip": str(int(response_body.gzip)),
                "resp_content_type": response_body.content_type,
            }
            async with client.pipeline(transaction=True) as pipeline:
                pipeline.hset(request_key, mapping=metadata)
                pipeline.expire(request_key, REQUEST_LOG_TTL_SECONDS)
                pipeline.set(body_key, request_body.stored_body)
                pipeline.expire(body_key, REQUEST_LOG_TTL_SECONDS)
                pipeline.set(response_key, response_body.stored_body)
                pipeline.expire(response_key, REQUEST_LOG_TTL_SECONDS)
                pipeline.zadd(user_key, {request_id: ts_ms})
                pipeline.expire(user_key, REQUEST_LOG_TTL_SECONDS)
                pipeline.zadd("req:all", {request_id: ts_ms})
                pipeline.expire("req:all", REQUEST_LOG_TTL_SECONDS)
                pipeline.hincrby(metrics_key, "count", 1)
                pipeline.hincrbyfloat(metrics_key, "total_duration_ms", duration_ms)
                pipeline.expire(metrics_key, REQUEST_LOG_TTL_SECONDS)
                results = await pipeline.execute()
            count, total_duration = int(results[10]), float(results[11])
            async with client.pipeline(transaction=True) as pipeline:
                pipeline.hset(metrics_key, "avg_duration_ms", total_duration / count)
                pipeline.expire(metrics_key, REQUEST_LOG_TTL_SECONDS)
                await pipeline.execute()
        except (RedisError, ValueError, TypeError, OverflowError, OSError) as error:
            logger.warning("Request logging Redis write failed: %s", error)

    @classmethod
    async def purge_expired_logs(cls, now_ms: int | None = None, *, force: bool = False) -> int:
        """Remove expired index members and their data, throttled across callers."""
        if not cls.is_enabled():
            return 0
        if not force and time.monotonic() - cls._last_purge_monotonic < (
            REQUEST_LOG_PURGE_INTERVAL_SECONDS
        ):
            return 0
        if cls._purge_lock is None:
            cls._purge_lock = asyncio.Lock()
        async with cls._purge_lock:
            client = cls._client
            if client is None:
                return 0
            if not force and time.monotonic() - cls._last_purge_monotonic < (
                REQUEST_LOG_PURGE_INTERVAL_SECONDS
            ):
                return 0
            cutoff = (int(time.time() * 1000) if now_ms is None else now_ms) - (
                REQUEST_LOG_TTL_SECONDS * 1000
            )
            expired_ids: set[str] = set()

            async def prune_index(key: str | bytes) -> None:
                while True:
                    batch = await client.zrangebyscore(
                        key, "-inf", cutoff, start=0, num=REQUEST_LOG_PURGE_BATCH_SIZE
                    )
                    if not batch:
                        return
                    expired_ids.update(request_id.decode("utf-8") for request_id in batch)
                    # Remove only this batch so subsequent reads can continue from offset zero.
                    await client.zrem(key, *batch)

            try:
                await prune_index("req:all")
                async for key in cls._scan_user_index_keys():
                    await prune_index(key)
                await cls._delete_request_data(tuple(expired_ids))
                cls._last_purge_monotonic = time.monotonic()
                return len(expired_ids)
            except RedisError as error:
                logger.warning("Request logging Redis purge failed: %s", error)
                return 0

    @classmethod
    async def _delete_request_data(
        cls, request_ids: Sequence[str], *, index_key: str = "req:all"
    ) -> None:
        """Delete request data and drop the IDs from the global index and `index_key`.

        Per-user indexes are not scanned here: the purge prunes all of them by score, and an
        orphan left in another user's index is pruned once its timestamp passes the cutoff.
        """
        client = cls._client
        if client is None or not request_ids:
            return
        request_ids = tuple(dict.fromkeys(request_ids))
        try:
            for offset in range(0, len(request_ids), REQUEST_LOG_PURGE_BATCH_SIZE):
                batch = request_ids[offset:offset + REQUEST_LOG_PURGE_BATCH_SIZE]
                async with client.pipeline(transaction=True) as pipeline:
                    pipeline.zrem("req:all", *batch)
                    if index_key != "req:all":
                        pipeline.zrem(index_key, *batch)
                    pipeline.delete(*(
                        key
                        for request_id in batch
                        for key in (
                            f"req:{request_id}", f"req:{request_id}:body",
                            f"req:{request_id}:response_body",
                        )
                    ))
                    await pipeline.execute()
        except RedisError as error:
            logger.warning("Request logging Redis deletion failed: %s", error)

    @classmethod
    async def _scan_user_index_keys(cls) -> AsyncIterator[bytes]:
        """Incrementally discover per-user indexes without blocking Redis with KEYS."""
        client = cls._client
        if client is None:
            return
        async for key in client.scan_iter(match="user:*:reqs", count=REQUEST_LOG_PURGE_BATCH_SIZE):
            yield key

    @classmethod
    async def _read_index(
        cls,
        key: str,
        *,
        start: int = 0,
        end: int = -1,
        start_ts: int | None = None,
        end_ts: int | None = None,
        count: int | None = None,
        by_ts: bool = False,
        count_only: bool = False,
    ) -> Any:
        """Centralize index reads, retention cleanup, and failure handling."""
        if not cls.is_enabled():
            return 0 if count_only else []
        try:
            await cls.purge_expired_logs()
            client = cls._client
            if client is None:
                return 0 if count_only else []
            minimum = "-inf" if start_ts is None else start_ts
            maximum = "+inf" if end_ts is None else end_ts
            if count_only:
                return int(
                    await client.zcount(key, minimum, maximum) if by_ts else await client.zcard(key)
                )
            if by_ts:
                if count is not None and count <= 0:
                    return []
                return await client.zrevrangebyscore(key, maximum, minimum, start=start, num=count)
            return await client.zrevrange(key, start, end)
        except RedisError as error:
            logger.warning("Request logging Redis index read failed: %s", error)
            return 0 if count_only else []

    @classmethod
    def _decode_entry(
        cls,
        request_id: str,
        metadata: Mapping[bytes, bytes],
        request_body: bytes | None,
        response_body: bytes | None,
    ) -> dict[str, Any]:
        """Expose decoded metadata and optional sanitized bodies through one path."""
        entry: dict[str, Any] = {
            key.decode("utf-8", errors="replace"): value.decode("utf-8", errors="replace")
            for key, value in metadata.items()
        }
        entry["request_id"] = request_id
        for field in ("ts", "status", "duration_ms", "req_body_len", "resp_body_len"):
            if field in entry:
                entry[field] = int(entry[field])
        for field in (
            "req_body_truncated",
            "req_body_gzip",
            "resp_body_truncated",
            "resp_body_gzip",
        ):
            if field in entry:
                entry[field] = entry[field].lower() in {"1", "true", "yes", "y"}
        if not entry.get("timestamp") and "ts" in entry:
            entry["timestamp"] = datetime.fromtimestamp(entry["ts"] / 1000, tz=UTC).isoformat()
        if request_body is not None:
            entry["body"] = cls._decode_stored_body(
                request_body, gzip_encoded=entry.get("req_body_gzip", False)
            )
        if response_body is not None:
            entry["response_body"] = cls._decode_stored_body(
                response_body, gzip_encoded=entry.get("resp_body_gzip", False)
            )
        return entry

    @classmethod
    async def _build_entries(
        cls,
        request_ids: Sequence[str | bytes],
        *,
        include_body: bool,
        index_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """Load entries; orphans are repaired only when the IDs came from `index_key`."""
        if not cls.is_enabled() or not request_ids:
            return []
        ids = [item.decode("utf-8") if isinstance(item, bytes) else item for item in request_ids]
        client = cls._client
        if client is None:
            return []
        try:
            async with client.pipeline(transaction=False) as pipeline:
                for request_id in ids:
                    pipeline.hgetall(f"req:{request_id}")
                if include_body:
                    for request_id in ids:
                        pipeline.get(f"req:{request_id}:body")
                    for request_id in ids:
                        pipeline.get(f"req:{request_id}:response_body")
                results = await pipeline.execute()
            entries = []
            missing = []
            size = len(ids)
            for index, request_id in enumerate(ids):
                if not results[index]:
                    missing.append(request_id)
                    continue
                entries.append(
                    cls._decode_entry(
                        request_id,
                        results[index],
                        results[size + index] if include_body else None,
                        results[2 * size + index] if include_body else None,
                    )
                )
            if missing and index_key is not None:
                await cls._delete_request_data(missing, index_key=index_key)
            return entries
        except (RedisError, ValueError, TypeError, OverflowError, OSError) as error:
            logger.warning("Request logging Redis entry read failed: %s", error)
            return []

    @classmethod
    async def get_request_by_id(
        cls, request_id: str, *, include_body: bool = True
    ) -> dict[str, Any] | None:
        entries = await cls._build_entries([request_id], include_body=include_body)
        return entries[0] if entries else None

    @classmethod
    async def get_request_ids_for_all(cls, start: int = 0, end: int = -1) -> list[bytes]:
        return await cls._read_index("req:all", start=start, end=end)

    @classmethod
    async def get_request_count_for_all(cls) -> int:
        return await cls._read_index("req:all", count_only=True)

    @classmethod
    async def get_requests_for_all(
        cls, start: int = 0, end: int = -1, *, include_body: bool = False
    ) -> list[dict[str, Any]]:
        ids = await cls.get_request_ids_for_all(start, end)
        return await cls._build_entries(ids, include_body=include_body, index_key="req:all")

    @classmethod
    async def get_request_ids_for_all_by_ts_range(
        cls, start_ts: int | None, end_ts: int | None, start: int = 0, count: int = 100
    ) -> list[bytes]:
        return await cls._read_index(
            "req:all", start_ts=start_ts, end_ts=end_ts, start=start, count=count, by_ts=True
        )

    @classmethod
    async def get_request_count_for_all_by_ts_range(
        cls, start_ts: int | None, end_ts: int | None
    ) -> int:
        return await cls._read_index(
            "req:all", count_only=True, start_ts=start_ts, end_ts=end_ts, by_ts=True
        )

    @classmethod
    async def get_requests_for_all_by_ts_range(
        cls,
        start_ts: int | None,
        end_ts: int | None,
        start: int = 0,
        count: int = 100,
        *,
        include_body: bool = False,
    ) -> list[dict[str, Any]]:
        ids = await cls.get_request_ids_for_all_by_ts_range(start_ts, end_ts, start, count)
        return await cls._build_entries(ids, include_body=include_body, index_key="req:all")

    @classmethod
    async def get_request_ids_for_user(
        cls, user_id: str, start: int = 0, end: int = -1
    ) -> list[bytes]:
        return await cls._read_index(f"user:{user_id}:reqs", start=start, end=end)

    @classmethod
    async def get_request_count_for_user(cls, user_id: str) -> int:
        return await cls._read_index(f"user:{user_id}:reqs", count_only=True)

    @classmethod
    async def get_requests_for_user(
        cls, user_id: str, start: int = 0, end: int = -1, *, include_body: bool = False
    ) -> list[dict[str, Any]]:
        ids = await cls.get_request_ids_for_user(user_id, start, end)
        return await cls._build_entries(
            ids, include_body=include_body, index_key=f"user:{user_id}:reqs"
        )

    @classmethod
    async def get_request_ids_for_user_by_ts_range(
        cls,
        user_id: str,
        start_ts: int | None,
        end_ts: int | None,
        start: int = 0,
        count: int = 100,
    ) -> list[bytes]:
        return await cls._read_index(
            f"user:{user_id}:reqs",
            start_ts=start_ts,
            end_ts=end_ts,
            start=start,
            count=count,
            by_ts=True,
        )

    @classmethod
    async def get_request_count_for_user_by_ts_range(
        cls, user_id: str, start_ts: int | None, end_ts: int | None
    ) -> int:
        return await cls._read_index(
            f"user:{user_id}:reqs", count_only=True, start_ts=start_ts, end_ts=end_ts, by_ts=True
        )

    @classmethod
    async def get_requests_for_user_by_ts_range(
        cls,
        user_id: str,
        start_ts: int | None,
        end_ts: int | None,
        start: int = 0,
        count: int = 100,
        *,
        include_body: bool = False,
    ) -> list[dict[str, Any]]:
        ids = await cls.get_request_ids_for_user_by_ts_range(
            user_id, start_ts, end_ts, start, count
        )
        return await cls._build_entries(
            ids, include_body=include_body, index_key=f"user:{user_id}:reqs"
        )

    @classmethod
    async def _scan_entries(
        cls,
        user_id: str | None,
        start_ts: int | None,
        end_ts: int | None,
        *,
        batch_size: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Scan metadata without loading bodies or skipping members after orphan repair."""
        if not cls.is_enabled():
            return
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        await cls.purge_expired_logs()
        client = cls._client
        if client is None:
            return
        key = "req:all" if user_id is None else f"user:{user_id}:reqs"
        offset = 0
        while True:
            ids = await client.zrevrangebyscore(
                key,
                "+inf" if end_ts is None else end_ts,
                "-inf" if start_ts is None else start_ts,
                start=offset,
                num=batch_size,
            )
            if not ids:
                return
            async with client.pipeline(transaction=False) as pipeline:
                for request_id in ids:
                    pipeline.hgetall(f"req:{request_id.decode('utf-8')}")
                metadata = await pipeline.execute()
            missing = []
            for request_id, fields in zip(ids, metadata, strict=True):
                decoded_id = request_id.decode("utf-8")
                if fields:
                    yield cls._decode_entry(decoded_id, fields, None, None)
                else:
                    missing.append(decoded_id)
            if missing:
                await client.zrem(key, *missing)
            await cls._delete_request_data(missing)
            # Orphan removal shifts the remaining members toward the beginning.
            offset += len(ids) - len(missing)
            if len(ids) < batch_size:
                return

    @classmethod
    async def get_requests_matching_path(
        cls,
        user_id: str | None = None,
        path_query: str = "",
        start_ts: int | None = None,
        end_ts: int | None = None,
        start: int = 0,
        count: int = 100,
        include_body: bool = False,
        batch_size: int = REQUEST_LOG_PURGE_BATCH_SIZE,
    ) -> tuple[int, list[dict[str, Any]]]:
        total = 0
        entries = []
        query = path_query.lower()
        try:
            async for entry in cls._scan_entries(user_id, start_ts, end_ts, batch_size=batch_size):
                if query not in entry.get("path", "").lower():
                    continue
                if start <= total < start + count:
                    entries.append(entry)
                total += 1
            if include_body:
                entries = await cls._build_entries(
                    [entry["request_id"] for entry in entries],
                    include_body=True,
                    index_key="req:all" if user_id is None else f"user:{user_id}:reqs",
                )
            return total, entries
        except (RedisError, ValueError, TypeError, OverflowError, OSError) as error:
            logger.warning("Request logging Redis path search failed: %s", error)
            return 0, []

    @classmethod
    async def get_request_log_metrics(
        cls,
        user_id: str | None = None,
        path_query: str | None = None,
        start_ts: int | None = None,
        end_ts: int | None = None,
        batch_size: int = REQUEST_LOG_PURGE_BATCH_SIZE,
    ) -> dict[str, Any]:
        neutral: dict[str, Any] = {
            "total_calls": 0,
            "average_response_time_ms": 0.0,
            "status_codes": {},
            "endpoints": [],
            "endpoint_groups": [],
        }
        total = 0
        duration_sum = 0
        statuses: dict[str, int] = {}
        endpoints: dict[tuple[str, str], list[int]] = {}
        groups: dict[str, list[int]] = {}
        query = (path_query or "").lower()
        try:
            async for entry in cls._scan_entries(user_id, start_ts, end_ts, batch_size=batch_size):
                path = entry.get("path", "")
                if query not in path.lower():
                    continue
                duration = entry.get("duration_ms", 0)
                total += 1
                duration_sum += duration
                status = str(entry.get("status") or "unknown")
                statuses[status] = statuses.get(status, 0) + 1
                endpoint = (entry.get("method", ""), path)
                values = endpoints.setdefault(endpoint, [0, 0])
                values[0] += 1
                values[1] += duration
                segments = path.strip("/").split("/")
                if segments[0] == "api":
                    segments = segments[1:]
                group = (segments[0] if segments else "") or "root"
                values = groups.setdefault(group, [0, 0])
                values[0] += 1
                values[1] += duration
            return {
                "total_calls": total,
                "average_response_time_ms": duration_sum / total if total else 0.0,
                "status_codes": statuses,
                "endpoints": sorted(
                    [
                        {
                            "method": method,
                            "path": path,
                            "count": calls,
                            "avg_duration_ms": duration / calls,
                        }
                        for (method, path), (calls, duration) in endpoints.items()
                    ],
                    key=lambda item: item["count"],
                    reverse=True,
                ),
                "endpoint_groups": sorted(
                    [
                        {"group": group, "count": calls, "avg_duration_ms": duration / calls}
                        for group, (calls, duration) in groups.items()
                    ],
                    key=lambda item: item["count"],
                    reverse=True,
                ),
            }
        except (RedisError, ValueError, TypeError, OverflowError, OSError) as error:
            logger.warning("Request logging Redis metrics read failed: %s", error)
            return neutral

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

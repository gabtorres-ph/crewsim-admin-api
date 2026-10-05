"""Class-level Redis lifecycle for request logging."""

import asyncio
import logging
from typing import ClassVar

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


class RequestLogManager:
    """Own the Redis client and background tasks for the application lifespan."""

    _client: ClassVar[Redis | None] = None
    _enabled: ClassVar[bool] = False
    _last_purge_monotonic: ClassVar[float] = 0.0
    _purge_lock: ClassVar[asyncio.Lock | None] = None
    _cleanup_task: ClassVar[asyncio.Task[None] | None] = None
    _write_tasks: ClassVar[set[asyncio.Task[None]]] = set()

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

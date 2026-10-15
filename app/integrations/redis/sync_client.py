"""Synchronous Redis client for blocking integrations that run in the threadpool."""

import logging
import threading

from redis import Redis
from redis.exceptions import RedisError

from app.config import Settings

logger = logging.getLogger(__name__)

SOCKET_TIMEOUT_SECONDS = 0.25

_client: Redis | None = None
_lock = threading.Lock()


def get_sync_redis(settings: Settings) -> Redis | None:
    """Return the shared client, or None when Redis is not configured or cannot be built."""
    global _client
    if not settings.redis_host:
        return None
    with _lock:
        if _client is None:
            try:
                _client = Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=0,
                    username=settings.redis_username or None,
                    password=settings.redis_password or None,
                    decode_responses=False,
                    socket_connect_timeout=SOCKET_TIMEOUT_SECONDS,
                    socket_timeout=SOCKET_TIMEOUT_SECONDS,
                )
            except (RedisError, ValueError, TypeError) as error:
                logger.warning("Sync Redis initialization failed: %s", type(error).__name__)
                return None
        return _client


def close_sync_redis() -> None:
    global _client
    with _lock:
        client, _client = _client, None
    if client is not None:
        try:
            client.close()
        except RedisError as error:
            logger.warning("Sync Redis close failed: %s", type(error).__name__)

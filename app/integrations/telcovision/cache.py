"""Short-lived Redis cache for Telcovision responses."""

import hashlib
import json
import logging
import secrets
import time
from collections.abc import Callable

from redis import Redis
from redis.exceptions import RedisError

from app.config import Settings
from app.integrations.redis.sync_client import get_sync_redis

logger = logging.getLogger(__name__)

KEY_PREFIX = "telcovision:v1"
LOCK_TTL_SECONDS = 10
LOCK_WAIT_SECONDS = 2.0
LOCK_POLL_SECONDS = 0.2

_warned_reasons: set[str] = set()


def _warn_once(reason: str) -> None:
    if reason not in _warned_reasons:
        _warned_reasons.add(reason)
        logger.warning("Telcovision cache disabled: %s", reason)


class TelcovisionCache:
    """Caches validated provider responses; every failure degrades to a live call."""

    def __init__(self, client: Redis, ttl_seconds: int, scope: str) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds
        # Hashed so environments sharing one Redis never collide and the URL is never stored.
        self._scope = hashlib.sha256(scope.encode()).hexdigest()

    @classmethod
    def from_settings(cls, settings: Settings, scope: str) -> "TelcovisionCache | None":
        """Return a cache, or None when caching is disabled or Redis is not configured."""
        if not settings.telcovision_cache_enabled:
            return None
        client = get_sync_redis(settings)
        if client is None:
            _warn_once("Redis is not configured")
            return None
        return cls(client, settings.telcovision_cache_ttl_seconds, scope)

    def _key(self, operation: str, payload: dict[str, object]) -> str:
        canonical = json.dumps(
            {"scope": self._scope, "operation": operation, "payload": payload},
            sort_keys=True,
            separators=(",", ":"),
        )
        return f"{KEY_PREFIX}:{operation}:{hashlib.sha256(canonical.encode()).hexdigest()}"

    @staticmethod
    def _short(key: str) -> str:
        return key.rsplit(":", 1)[-1][:12]

    def _read(
        self,
        key: str,
        request_id: str,
        validate: Callable[[dict[str, object]], object] | None,
    ) -> dict[str, object] | None:
        try:
            raw = self._client.get(key)
        except RedisError as error:
            logger.warning(
                "Telcovision cache read failed request_id=%s error=%s",
                request_id,
                type(error).__name__,
            )
            return None
        if raw is None:
            return None

        try:
            envelope = json.loads(raw)
            body = envelope["body"]
            stored_at = float(envelope["stored_at"])
            if not isinstance(body, dict):
                raise TypeError
            if validate is not None:
                validate(body)
        except Exception as error:  # noqa: BLE001 - any unreadable or invalid entry is evicted
            logger.warning(
                "Telcovision cache entry rejected request_id=%s key=%s error=%s",
                request_id,
                self._short(key),
                type(error).__name__,
            )
            self._delete(key, request_id)
            return None

        logger.info(
            "Telcovision cache hit request_id=%s key=%s age_s=%.1f",
            request_id,
            self._short(key),
            max(time.time() - stored_at, 0.0),
        )
        return body

    def _write(self, key: str, body: dict[str, object], request_id: str) -> None:
        try:
            envelope = json.dumps({"stored_at": time.time(), "body": body}).encode()
            self._client.set(key, envelope, ex=self._ttl_seconds)
        except (RedisError, TypeError, ValueError) as error:
            logger.warning(
                "Telcovision cache write failed request_id=%s error=%s",
                request_id,
                type(error).__name__,
            )

    def _delete(self, key: str, request_id: str) -> None:
        try:
            self._client.delete(key)
        except RedisError as error:
            logger.warning(
                "Telcovision cache delete failed request_id=%s error=%s",
                request_id,
                type(error).__name__,
            )

    def _acquire_lock(self, lock_key: str, token: str, request_id: str) -> bool:
        try:
            return bool(self._client.set(lock_key, token, nx=True, ex=LOCK_TTL_SECONDS))
        except RedisError as error:
            logger.warning(
                "Telcovision cache lock failed request_id=%s error=%s",
                request_id,
                type(error).__name__,
            )
            return True  # Redis is unhealthy, so waiting for another worker would only add delay.

    def _release_lock(self, lock_key: str, token: str) -> None:
        try:
            if self._client.get(lock_key) == token.encode():
                self._client.delete(lock_key)
        except RedisError:
            pass  # The lock expires on its own.

    def fetch(
        self,
        operation: str,
        payload: dict[str, object],
        loader: Callable[[], dict[str, object]],
        *,
        request_id: str,
        bypass: bool = False,
        validate: Callable[[dict[str, object]], object] | None = None,
    ) -> dict[str, object]:
        """Return a cached body, else call `loader` and cache its already-validated result."""
        key = self._key(operation, payload)
        short = self._short(key)

        if bypass:
            logger.info("Telcovision cache bypass request_id=%s key=%s", request_id, short)
            body = loader()
            self._write(key, body, request_id)
            return body

        cached = self._read(key, request_id, validate)
        if cached is not None:
            return cached
        logger.info("Telcovision cache miss request_id=%s key=%s", request_id, short)

        lock_key = f"{key}:lock"
        token = secrets.token_hex(8)
        if not self._acquire_lock(lock_key, token, request_id):
            # Another worker is fetching; wait briefly for its result, then fall through live.
            deadline = time.monotonic() + LOCK_WAIT_SECONDS
            while time.monotonic() < deadline:
                time.sleep(LOCK_POLL_SECONDS)
                cached = self._read(key, request_id, validate)
                if cached is not None:
                    return cached
        try:
            body = loader()
            self._write(key, body, request_id)
            return body
        finally:
            self._release_lock(lock_key, token)

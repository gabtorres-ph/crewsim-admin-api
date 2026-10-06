# Plan: Redis-backed request logging

## Context

Implement the subsystem described in [request-logging.md](request-logging.md), adapted to this
FastAPI application. The result will capture sanitized request/response bodies, persist three days
of logs in Redis, expose query and metrics endpoints, and remain non-blocking when Redis is disabled
or unavailable.

The repository is on `main` with no tracked modifications. The reference document is currently
untracked and will remain unchanged.

## Scope

- In scope: Redis lifecycle, request middleware, redaction/compression, TTL and index cleanup, log
  queries, metrics, pagination, configuration, route registration, and operational documentation.
- In scope: Safe improvements identified by the reference—resolved route templates, direct-peer caller IP
  attribution, tracked background writes, interrupted-stream logging, and shared decoding logic.
- Non-goals: PostgreSQL models or migrations, database-query logging context, the source system's
  webhook/siphon pseudo-users, or its `/accounts/current (login)` relabel.
- Non-goals: Building a new identity/role system solely for these endpoints.
- Non-goals: Automated test implementation or execution; validation remains with the human.

## Design decisions

- Architecture: Put Redis-specific behavior in `app/integrations/redis/` and administrative HTTP
  behavior in `app/utils/`. Rejected forcing Redis through the SQLAlchemy domain layers because it
  is external infrastructure with a different lifecycle and persistence model.
- Compatibility: Preserve the constants, key names, metadata fields, TTLs, query semantics, and
  response shapes from the reference.
- Middleware: Use the existing Starlette HTTP middleware mechanism, capture the request before
  dispatch, and resolve `request.scope["route"].path` after routing. Rejected pre-dispatch route
  resolution because it would record concrete IDs instead of route templates.
- Response capture: Support buffered and streaming responses; stream chunks unchanged and schedule
  logging in `finally` so partial/erroring streams are still represented.
- Background writes: Retain fire-and-forget request behavior, but hold strong references to tasks
  and drain them for up to five seconds during shutdown. Rejected untracked `create_task()` calls
  because they can lose writes.
- Redis writes: Retain the transactional pipeline and the currently write-only `req:metrics:*`
  hashes for specification compatibility. Rejected removing them even though endpoint metrics are
  recomputed.
- Redis failure behavior: Log warnings and return neutral results without affecting application
  responses. No retries will occur in request handling.
- Caller IP: Use `request.client.host`, the direct peer address, and ignore forwarded headers.
- User attribution: Read `request.state.user_id` after endpoint processing and fall back to
  `"anonymous"`. The application currently has no auth component setting this value.
- Administration boundary: Assume the existing Cloudflare Access protection described in the
  README is the admin authorization boundary for the whole service. Rejected inventing an
  application-level role header because there is no authenticated identity or trusted role source
  in the codebase.
- Pagination: Introduce a reusable `PaginatedResponse[T]`. `page_size` overrides `limit`; `start`
  overrides the computed offset. When `start` is supplied, the returned page is
  `start // effective_limit + 1`.
- Body safety: Preserve reference behavior exactly—headers are never logged, JSON/form sensitive
  keys are redacted recursively, binary bodies are omitted without being read, storage is capped
  at 32 KiB, and values over 1 KiB are gzipped.
- Data model: Redis only; no Alembic migration is required.
- Configuration: Use only `REDIS_HOST`, `REDIS_PORT`, `REDIS_USERNAME`, and `REDIS_PASSWORD`
  for the Redis connection. An empty host disables logging. Use database 0; empty credentials
  mean no authentication. There is no logging toggle or trusted-proxy setting.
- Deployment: Preserve the existing Compose Redis service and pass the four connection variables
  through the shared application environment.

## Files affected

- New: `app/integrations/__init__.py`: integration package marker.
- New: `app/integrations/redis/__init__.py`: Redis integration package marker.
- New: `app/integrations/redis/request_logging.py`: manager, capture, storage, cleanup, and query
  behavior.
- New: `app/integrations/redis/request_logging_middleware.py`: HTTP request/response wrapper.
- New: `app/common/schemas.py`: reusable pagination response.
- New: `app/utils/__init__.py`: utilities API package marker.
- New: `app/utils/schemas.py`: request-log and metrics response models.
- New: `app/utils/routes.py`: request-log administration endpoints.
- Modified: `app/config.py`: Redis host, port, username, and password settings.
- Modified: `app/main.py`: lifespan and middleware registration.
- Modified: `app/routes.py`: utilities router registration.
- Modified: `.env.example`: documented request-logging settings.
- Modified: `compose.yaml`: pass request-logging settings into the API container.
- Modified: `pyproject.toml`: add the async Redis client dependency.
- Modified: `uv.lock`: lock the Redis dependency.
- Modified: `requirements.lock`: include Redis in the runtime image.
- Modified: `README.md`: setup, security, and operational behavior.

## Steps

### Step 1: Add the Redis runtime dependency

- **Goal:** Make `redis.asyncio` available in development and production.
- **Files:** `pyproject.toml`, `uv.lock`, `requirements.lock`
- **Instructions:**
  - Add `redis>=5.0.0` to project dependencies.
  - Regenerate `uv.lock`.
  - Re-export `requirements.lock` using the repository's documented UV command so the Docker image
    receives the same resolved Redis version.
  - Do not add a synchronous Redis library or a second client implementation.
- **Reuse:** `README.md`: dependency update commands.
- **Depends on:** none
- **Done when:** All three dependency manifests consistently contain redis-py.

### Step 2: Add request-logging configuration

- **Goal:** Expose the Redis connection using four environment variables.
- **Files:** `app/config.py`, `.env.example`, `compose.yaml`
- **Instructions:**
  - Add `redis_host: str = Field(default="", alias="REDIS_HOST")`.
  - Add `redis_port: int = Field(default=6379, alias="REDIS_PORT", ge=1, le=65535)`.
  - Add `redis_username: str = Field(default="", alias="REDIS_USERNAME")`.
  - Add `redis_password: str = Field(default="", alias="REDIS_PASSWORD")`.
  - Document all four variables in `.env.example`, retaining host `redis` and port `6379`
    for local Compose, with username `default` and a generic development password. Local Compose
    Redis requires a nonempty password and uses an authenticated healthcheck.
  - Pass all four variables through `x-app-environment`. Default the host to `redis` only
    when unset, preserving an explicitly empty host to disable logging.
  - Remove the application Redis database variable; use database 0.
  - Do not add a URL, logging toggle, or trusted-proxy configuration.
- **Reuse:** Existing Redis host/port variables and DB port validation pattern.
- **Depends on:** none
- **Done when:** Settings expose the four connection values, validate the port, and allow an empty
  host to disable logging.

### Step 3: Create the Redis manager lifecycle

- **Goal:** Establish a class-level manager that degrades safely.
- **Files:** `app/integrations/__init__.py`, `app/integrations/redis/__init__.py`,
  `app/integrations/redis/request_logging.py`
- **Instructions:**
  - Define the reference constants, plus `REQUEST_LOG_SHUTDOWN_TIMEOUT_SECONDS = 5`.
  - Define class state for `_client`, `_enabled`, `_last_purge_monotonic`, `_purge_lock`,
    `_cleanup_task`, and `_write_tasks`.
  - Implement:
    - `init(cls, host: str, port: int = 6379, *, username: str = "", password: str = "") -> None`
    - `is_enabled(cls) -> bool`
    - `start_cleanup_task(cls) -> None`
    - `close(cls) -> None`
  - Disable the manager for an empty host. Otherwise construct the async Redis client with host,
    port, database 0, optional credentials (`None` for empty strings), and `decode_responses=False`.
  - Run forced cleanup every 60 seconds; warn and continue after Redis errors.
  - During close, cancel cleanup, allow tracked writes five seconds to finish, cancel remaining
    tasks, call `Redis.aclose()`, and reset all class state.
- **Reuse:** `app/main.py`: application-level composition conventions.
- **Depends on:** Steps 1–2
- **Done when:** The manager starts, stops, and remains disabled for missing/invalid configuration
  without preventing application startup.

### Step 4: Implement body capture and sanitization

- **Goal:** Produce safe `RequestBodySnapshot` values matching the reference.
- **Files:** `app/integrations/redis/request_logging.py`
- **Instructions:**
  - Add `RequestBodySnapshot` with `content_type`, `raw_length`, `stored_body`, `truncated`, and
    `gzip`.
  - Implement content-type normalization and the textual/omitted rules from section 5.
  - Implement sensitive-key normalization and recursive replacement with `"[REDACTED]"`.
  - Implement:
    - `capture_body(cls, request: Request) -> RequestBodySnapshot`
    - `capture_response_body(cls, body: bytes, content_type: str, *, raw_length: int | None = None) -> RequestBodySnapshot`
    - `_decode_stored_body(cls, body: bytes, *, gzip_encoded: bool) -> Any`
  - Never read omitted request bodies; use `Content-Length` for their placeholder.
  - Redact JSON and form data before truncation, cap stored content at 32 KiB, and gzip content over
    1 KiB.
  - Preserve the reference behavior that plain text, XML, and GraphQL are not structurally
    redacted.
- **Reuse:** [request-logging.md](request-logging.md): sections 5.1–5.3.
- **Depends on:** Step 3
- **Done when:** Every request/response body can be represented without logging headers or
  unrestricted binary data.

### Step 5: Implement Redis writes and expiry repair

- **Goal:** Persist request records atomically and keep indexes bounded.
- **Files:** `app/integrations/redis/request_logging.py`
- **Instructions:**
  - Implement `schedule_log(cls, **log_data: Any) -> None` to create and track a task without
    awaiting it.
  - Implement `log_request(...) -> None` with typed keyword arguments for the request ID,
    timestamp, attribution, method/path/status/duration, and two optional snapshots.
  - Write the metadata hash, both body keys, global/per-user indexes, and endpoint metrics in one
    transactional pipeline.
  - Apply the three-day TTL to every touched key and update `avg_duration_ms` after reading pipeline
    count/total results.
  - Implement:
    - `purge_expired_logs(cls, now_ms: int | None = None, *, force: bool = False) -> int`
    - `_delete_request_data(cls, request_ids: Sequence[str]) -> None`
    - `_scan_user_index_keys(cls) -> AsyncIterator[bytes]`
  - Use the monotonic 60-second guard with a lazily initialized lock and batches of 500.
  - Deduplicate expired IDs before deletion.
  - Catch Redis exceptions, emit warnings, and never re-raise into request handling.
- **Reuse:** Reference Redis schema and pipeline in sections 7.1–7.2.
- **Depends on:** Steps 3–4
- **Done when:** Written records have the documented keys/fields/TTLs and stale sorted-set members
  are repairable.

### Step 6: Implement request-log queries and aggregation

- **Goal:** Provide all manager operations required by the HTTP API.
- **Files:** `app/integrations/redis/request_logging.py`
- **Instructions:**
  - Implement the global and per-user ID, count, timestamp-range, and entry methods listed in
    section 8.
  - Implement:
    - `_build_entries(cls, request_ids: Sequence[str | bytes], *, include_body: bool) -> list[dict[str, Any]]`
    - `_decode_entry(cls, request_id: str, metadata: Mapping[bytes, bytes], request_body: bytes | None, response_body: bytes | None) -> dict[str, Any]`
    - `get_requests_matching_path(...) -> tuple[int, list[dict[str, Any]]]`
    - `get_request_log_metrics(...) -> dict[str, Any]`
    - `get_request_by_id(request_id: str, *, include_body: bool) -> dict[str, Any] | None`
  - Pipeline metadata/body reads, preserve requested ordering, convert numeric/boolean fields,
    synthesize missing ISO timestamps, and use the shared body decoder.
  - Lazily delete index members whose hashes are absent.
  - Apply case-insensitive path substring matching in batches of 500.
  - Calculate total calls, mean duration, status counts, endpoint metrics, and endpoint-group metrics
    exactly as documented.
  - Return empty/neutral results when disabled or Redis operations fail.
- **Reuse:** Reference method matrix and metrics rules in section 8.
- **Depends on:** Step 5
- **Done when:** The manager can serve list, filtered list, detail, and metrics operations without
  exposing raw Redis values.

### Step 7: Add request/response middleware

- **Goal:** Capture every eligible request without delaying its response on Redis.
- **Files:** `app/integrations/redis/request_logging_middleware.py`
- **Instructions:**
  - Implement
    `handle_request_logging(request: Request, call_next: RequestResponseEndpoint) -> Response`.
  - Generate `uuid4().hex`, assign `request.state.request_id`, and record epoch milliseconds before
    dispatch.
  - Capture textual request bodies before dispatch only when logging is enabled.
  - Time `call_next`; on exceptions, schedule status `500` without a response body and re-raise.
  - Resolve the route template after dispatch, normalize `{parameter}` to `:parameter`, and fall
    back to the raw URL path.
  - Resolve `user_id` from `request.state.user_id` after dispatch or use `"anonymous"`.
  - Resolve caller IP from `request.client.host`; ignore forwarded headers.
  - Skip status `307`.
  - Capture buffered responses immediately; wrap async or sync body iterators so all chunks are
    returned unchanged while at most 32 KiB is copied.
  - Schedule streaming logs in `finally`, including partial streams, and measure duration through
    stream completion.
- **Reuse:** `app/common/cors.py`: isolated middleware integration style.
- **Depends on:** Steps 2, 4–6
- **Done when:** Handlers still receive their request body, clients receive unchanged responses, and
  Redis work is scheduled outside response latency.

### Step 8: Define API response schemas

- **Goal:** Give the administrative endpoints stable typed responses.
- **Files:** `app/common/schemas.py`, `app/utils/__init__.py`, `app/utils/schemas.py`
- **Instructions:**
  - Add generic `PaginatedResponse[T]` with `items`, `total`, `page`, and `limit`.
  - Add `RequestLogEntry` with every field and optional body field from section 9; use
    `ConfigDict(extra="allow")`.
  - Add `RequestLogEndpointMetrics`, `RequestLogGroupMetrics`, and `RequestLogMetricsResponse`.
  - Use `Field(default_factory=...)` for collections.
- **Reuse:** Existing Pydantic v2 schemas such as `app/usage/schemas.py`.
- **Depends on:** none
- **Done when:** All documented list, detail, and metrics payloads validate without losing extra
  Redis metadata.

### Step 9: Add request-log administration routes

- **Goal:** Expose list, metrics, and detail operations under `/api/utils/request-logs`.
- **Files:** `app/utils/routes.py`, `app/routes.py`
- **Instructions:**
  - Create an `APIRouter(prefix="/utils/request-logs", tags=["request-logs"])`.
  - Implement helpers that convert naive datetimes as UTC, convert aware datetimes to epoch
    milliseconds, reject `to < from` with 400, and return 503 when logging is disabled.
  - Add `GET ""` with `user_id`, `path`, aliased `from`/`to`, `include_body=False`, `page>=1`,
    `limit=100`, optional `page_size`, and optional `start`.
  - Select path-scan, time-range, per-user, or global manager operations exactly as section 9
    specifies.
  - Add `GET "/metrics"` before the dynamic route.
  - Add `GET "/{request_id}"` with `include_body=True` and a 404 response for missing records.
  - Register the router in the central `api_router`.
- **Reuse:** `app/routes.py`: central router registry; `app/usage/routes.py`: typed `Query`/`Path`
  conventions.
- **Depends on:** Steps 6 and 8
- **Done when:** All three endpoint shapes, validation rules, status codes, and defaults match the
  reference.

### Step 10: Wire middleware and lifecycle into FastAPI

- **Goal:** Activate request logging through the application composition root.
- **Files:** `app/main.py`
- **Instructions:**
  - Add an `asynccontextmanager` lifespan that initializes the manager with the configured Redis
    host, port, username, and password, starts cleanup, yields, and always closes the manager.
  - Pass the lifespan to `FastAPI`.
  - Register a thin HTTP middleware function that delegates to `handle_request_logging`.
  - Keep CORS, exception handlers, API registration, `/`, and `/health` behavior unchanged.
- **Reuse:** `app/main.py`: existing composition root.
- **Depends on:** Steps 2, 3, 7, and 9
- **Done when:** Startup/shutdown owns Redis resources and every application request passes through
  logging.

### Step 11: Document setup and operations

- **Goal:** Make deployment requirements and security behavior explicit.
- **Files:** `README.md`
- **Instructions:**
  - Document `REDIS_HOST`, `REDIS_PORT`, `REDIS_USERNAME`, and `REDIS_PASSWORD`, including
    empty-host disabling, optional credentials, and fixed database 0.
  - State that missing/unreachable Redis does not block API traffic.
  - Document the three administrative endpoints, three-day retention, body limits, redaction
    behavior, and possible truncated JSON strings.
  - Explain that Cloudflare Access is assumed to provide the admin boundary.
  - Warn that body logging is enabled when a Redis host is configured and that plain/XML/GraphQL content does not receive
    key-based redaction.
- **Reuse:** Existing configuration and Cloudflare sections in `README.md`.
- **Depends on:** Steps 2 and 9–10
- **Done when:** An operator can configure, secure, and troubleshoot the feature without reading
  its implementation.

## Risks and mitigations

- Sensitive information in non-JSON text: Document the limitation and retain the reference
  behavior; callers should not send credentials in these formats.
- Redis latency/outage: All writes are background tasks, operations swallow Redis errors, and
  shutdown draining is bounded.
- High-volume path searches and metrics: Preserve the O(N) reference behavior initially; document
  that a secondary index or log-oriented datastore is the scaling path.
- Task growth under sustained Redis slowness: Configure short Redis socket/connect timeouts and
  track task count through application logs.
- Spoofed caller IP: Ignore forwarded headers and record the direct peer. Behind a reverse proxy,
  this records the proxy address rather than the originating client.
- Lost route cardinality control: Read the matched route after dispatch so `/users/123` is stored
  as `/users/:user_id`.
- Index orphans: Combine scheduled purge, opportunistic purge, and lazy repair on reads.
- Redis key growth from endpoint metrics: Keep the compatibility keys but normalize route templates
  before forming them.
- Missing in-process admin roles: Rely on the existing application-wide Cloudflare Access boundary
  unless the project adds a validated user identity system.

## Manual verification (for the human)

- Start with an empty `REDIS_HOST`; verify `/health` still returns 200 and request-log endpoints return
  503.
- Start with an empty `REDIS_HOST`; verify no Redis keys are written.
- Verify optional Redis credentials and rejection of ports outside 1–65535.
- Configure Redis and verify metadata, body keys, both indexes, metrics, and three-day TTLs.
- Verify nested JSON and form secrets are redacted, headers are absent, binary bodies produce
  omission placeholders, large bodies truncate, and bodies over 1 KiB gzip/decode correctly.
- Verify a route such as `/api/users/123` is recorded using its normalized template.
- Verify response chunks are unchanged for streaming endpoints and partial streams still schedule
  a record.
- Verify handler exceptions are re-raised while a status-500 record is scheduled.
- Verify 307 responses are not recorded.
- Verify `X-Forwarded-For` cannot change the recorded direct-peer caller IP.
- Exercise pagination precedence, user filters, timestamp ranges, path matching, metrics, detail
  bodies, 400 invalid ranges, and 404 unknown IDs.
- Delete a request hash while leaving its index member; verify the next read repairs the orphan.
- Insert expired index members and verify forced/background purge removes indexes and request keys.
- Stop the application with pending writes and verify shutdown drains or cancels them within five
  seconds.
- Run the project's test suite, Ruff checks, and dependency/package build after implementation.

## Open questions

- Does the existing Cloudflare Access perimeter satisfy the "admin-only" requirement? This plan
  assumes yes. If application-level user roles are required, the authentication contract must be
  defined before implementation.

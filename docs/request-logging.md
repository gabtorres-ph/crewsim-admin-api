# Request Logging (Redis-backed)

This document describes the HTTP request/response logging subsystem in `core.mytello.com` well enough to re-implement it in another codebase. It covers what is captured, how it is stored in Redis, how it expires, how it is queried, and which parts are specific to this application.

Source files:

| File | Role |
|---|---|
| `app/integrations/redis/request_logging.py` | `RequestLogManager`: body capture/redaction, Redis writes, cleanup, queries |
| `app/integrations/redis/request_logging_middleware.py` | `handle_request_logging`: per-request wrapper around `call_next` |
| `app/main.py` | Registers the middleware; init/cleanup/close on startup/shutdown |
| `app/utils/routes.py` | Admin endpoints under `/api/utils/request-logs` |
| `app/utils/schemas.py` | `RequestLogEntry`, `RequestLogMetricsResponse` response models |
| `app/integrations/redis/test_request_logging.py` | Unit tests with a fake Redis client |

---

## 1. Overview

- Every HTTP request passing through the app middleware is recorded: metadata (method, path, status, duration, caller IP, user id) plus a **redacted, truncated, optionally gzipped** copy of the request and response bodies.
- Records are stored in Redis with a **3-day TTL** and indexed by time in two sorted sets: a global index and a per-user index.
- The Redis write happens in a **fire-and-forget background task** so logging never delays or breaks the response.
- Admins can list, filter (user, path substring, time range), page, aggregate and inspect individual requests via HTTP endpoints.
- The whole feature turns into a no-op if disabled or if Redis is unavailable; every public method checks `is_enabled()` first.

Stack in the original: FastAPI/Starlette, `redis.asyncio` (redis-py ≥ 4.2), Python 3.10+, Pydantic v2.

---

## 2. Configuration and constants

| Setting | Default | Meaning |
|---|---|---|
| `REDIS_URL` | `None` | Redis connection URL. `redis://` is prepended if no scheme is given. |
| `REQUEST_LOGGING_ENABLED` | `True` | Master switch. |

| Constant | Value | Purpose |
|---|---|---|
| `REQUEST_LOG_TTL_SECONDS` | `259200` (3 days) | TTL on every key; also the cutoff for index pruning |
| `REQUEST_LOG_PURGE_INTERVAL_SECONDS` | `60` | Minimum interval between purges |
| `REQUEST_LOG_PURGE_BATCH_SIZE` | `500` | Batch size for `ZRANGEBYSCORE` / `SCAN` during purge |
| `MAX_BODY_BYTES` | `32 * 1024` | Max stored bytes per body (request and response) |
| `MAX_CAPTURE_BYTES` | `256 * 1024` | Max bytes buffered from a streamed response so it can be redacted before truncation |
| `COMPRESS_THRESHOLD_BYTES` | `1024` | Bodies larger than this are gzipped before storage |
| `MAX_PATH_LENGTH` | `256` | Raw URL paths of unmatched requests are cut to this length in the metadata |
| `UNMATCHED_PATH` | `"__unmatched__"` | Path segment of the metrics key for requests that matched no route |
| `METRICS_METHODS` | standard HTTP methods | Other methods are grouped as `OTHER` in the metrics key |
| `REDACTED_VALUE` | `"[REDACTED]"` | Replacement for sensitive values |

---

## 3. Lifecycle

`RequestLogManager` is a class-level singleton (all state on the class: `_client`, `_enabled`, `_last_purge_monotonic`, `_purge_lock`, `_cleanup_task`).

**Startup**

1. `RequestLogManager.init(redis_url, enabled=...)`
   - Returns silently if `enabled` is false.
   - Logs a warning and stays disabled if the URL is missing, the `redis` package cannot be imported, or `redis.from_url` raises `ValueError`.
   - Creates the client with `decode_responses=False` (bodies are bytes, possibly gzip).
2. `await RequestLogManager.start_cleanup_task()` starts an `asyncio` task that calls `purge_expired_logs(force=True)` every 60 s, logging and continuing on errors.

**Shutdown**

`await RequestLogManager.close()` cancels the cleanup task, closes the client and resets all state.

`is_enabled()` returns `_enabled and _client is not None`.

---

## 4. Request flow

The middleware (`sentry_http_metrics` in `main.py`) calls:

```python
endpoint = getattr(request.scope.get("route"), "path", request.url.path)
response = await handle_request_logging(request, call_next, endpoint=endpoint, method=request.method)
```

`handle_request_logging` then:

1. `normalized_path = normalize_path(endpoint)`: rewrites `{param}` to `:param`.
2. Generates `request_id = uuid4().hex`, stores it on `request.state.request_id`, records `ts_ms = int(time.time() * 1000)`.
3. If enabled, `body_snapshot = await capture_body(request)`. This reads `request.body()`, which Starlette caches so the handler can still read it.
4. *(App-specific, optional)* `set_query_request_context(method, endpoint)` puts method/endpoint into a `ContextVar` so SQL query logging can attribute queries to the endpoint; it is reset in `finally`.
5. Times `await call_next(request)` with `time.perf_counter()`.
   - **On exception:** schedule a log with status `500` (no response body), then re-raise.
6. Captures the response body:
   - **Buffered response** (has non-empty `.body`): `capture_response_body(response.body, content_type)` and schedule the log immediately.
   - **Streaming response** (has `.body_iterator`): replace the iterator with a wrapper generator that yields every chunk unchanged while copying up to `MAX_CAPTURE_BYTES` and counting the total length. After the last chunk it calls `capture_response_body(captured, content_type, raw_length=total)` and schedules the log. Handles both async and sync iterators.
   - **Neither:** schedule the log without a response body.
7. Returns the response.

> **Note:** with `@app.middleware("http")` (Starlette's `BaseHTTPMiddleware`), `call_next` *always* returns a `_StreamingResponse` with a `body_iterator` and no `.body` (verified on Starlette 1.6.0). So in this app every response actually takes the streaming branch, and the buffered branch only matters if the logic is reused somewhere `call_next` returns real `Response` objects. In the port, either keep both branches or implement the capture as pure ASGI middleware that wraps `send` and collects `http.response.body` messages.

**`_schedule_log(status, duration_ms, response_snapshot, response_content_type)`**

- Skips if logging is disabled or `status == 307` (trailing-slash redirects are noise).
- Resolves `caller_ip` and `user_id` (see §6). This runs *after* the handler, so values set on `request.state` by auth dependencies are available.
- *(App-specific)* Relabels path `/api/accounts/current` as `/api/accounts/current (login)`.
- `asyncio.create_task(log_request(...))`: fire-and-forget.

### Sequence diagram

```
Client        Middleware           RequestLogManager       Route+auth         Redis
   |               |                       |                    |               |
   | HTTP request  |                       |                    |               |
   |-------------->|                       |                    |               |
   |               |-- request_id = uuid4, ts_ms                |               |
   |               | normalize_path(endpoint)                   |               |
   |               |---------------------->|                    |               |
   |               | capture_body(request) |                    |               |
   |               |---------------------->|                    |               |
   |               |                       | binary? -> {omitted}; else         |
   |               |                       | redact, cut 32KB, gzip >1KB        |
   |               | RequestBodySnapshot   |                    |               |
   |               |<----------------------|                    |               |
   |               |-- set_query_request_context                |               |
   |               | call_next(request)    |                    |               |
   |               |------------------------------------------->|               |
   |               |                       |                    | auth sets state.user_id
== alt: handler raises =================================================================
   |               | exception             |                    |               |
   |               |<-------------------------------------------|               |
   |               |-- _schedule_log(500) (see below)           |               |
   | re-raise -> 500                       |                    |               |
   |<--------------|                       |                    |               |
== alt: buffered response (.body) ======================================================
   |               | response              |                    |               |
   |               |<-------------------------------------------|               |
   |               | capture_response_body(body)                |               |
   |               |---------------------->|                    |               |
   |               | response snapshot     |                    |               |
   |               |<----------------------|                    |               |
   |               |-- _schedule_log(status, ...)               |               |
   | response      |                       |                    |               |
   |<--------------|                       |                    |               |
== alt: streaming response (.body_iterator) ============================================
   |               | StreamingResponse     |                    |               |
   |               |<-------------------------------------------|               |
   |               |-- wrap iterator: capture_and_yield         |               |
   | response (streaming starts)           |                    |               |
   |<--------------|                       |                    |               |
   |               | loop per chunk: copy <=256KB, yield        |               |
   | chunk ...     |                       |                    |               |
   |<--------------|                       |                    |               |
   |               | after last chunk:     |                    |               |
   |               | capture_response_body(captured)            |               |
   |               |---------------------->|                    |               |
   |               |-- _schedule_log(status, ...)               |               |
== _schedule_log (skips 307) ===========================================================
   |               | get_caller_ip(request)|                    |               |
   |               |---------------------->|                    |               |
   |               | resolve_user_id(...)  |                    |               |
   |               |---------------------->|                    |               |
   |               | create_task(log_request(...))              |               |
   |               |---------------------->|                    |               |
   |               | fire-and-forget; response not blocked      |               |
== background task: log_request ========================================================
   |               |                       | purge_expired_logs() (<=1x/min)    |
   |               |                       |----------------------------------->|
   |               |                       | MULTI pipeline:    |               |
   |               |                       |----------------------------------->|
   |               |                       |                    |               | HSET req:{id} metadata
   |               |                       |                    |               | SET req:{id}:body
   |               |                       |                    |               | SET req:{id}:response_body
   |               |                       |                    |               | ZADD user:{uid}:reqs, req:all
   |               |                       |                    |               | HINCRBY req:metrics:{m}:{p}
   |               |                       |                    |               | EXPIRE all keys 3d
   |               |                       | count, total_duration              |
   |               |                       |<-----------------------------------|
   |               |                       | HSET req:metrics avg_duration_ms   |
   |               |                       |----------------------------------->|
```

---

## 5. Body capture

Both request and response bodies become a `RequestBodySnapshot`:

```python
@dataclass
class RequestBodySnapshot:
    content_type: str   # original header value
    raw_length: int     # original size in bytes, before redaction/truncation
    stored_body: bytes  # what gets written to Redis
    truncated: bool
    gzip: bool
```

### 5.1 Content-type classification

The base content type is the header up to the first `;`, stripped and lowercased.

**Omitted (not stored)** when the base type:
- starts with `multipart/`, `image/`, `audio/` or `video/`, or
- is `application/octet-stream`, `application/pdf`, `application/zip` or `application/x-zip-compressed`, or
- starts with `application/` and is not textual.

**Textual** when the base type is empty, starts with `text/`, contains `json`, or is one of `application/json`, `application/x-www-form-urlencoded`, `application/xml`, `application/graphql`.

For omitted bodies the request body is **never read**, and the stored value is a JSON placeholder:

```json
{"omitted": true, "reason": "binary_or_multipart", "content_type": "image/png", "content_length": 12345}
```

For requests, `content_length` comes from the `Content-Length` header; for responses, it comes from the measured length.

The same placeholder shape is used whenever a textual body cannot be safely stored. **A body that cannot be redacted is never stored raw.** The `reason` field says why:

| `reason` | When |
|---|---|
| `binary_or_multipart` | Omitted content type (above) |
| `too_large` | A streamed body longer than `MAX_CAPTURE_BYTES`, so only part of it was captured |
| `unparseable_json` | The body is treated as JSON (§5.2) but does not parse, or is nested too deeply to parse or redact (`RecursionError`) |
| `capture_failed` | Any other exception during capture; it is logged as a warning, and the request is unaffected |

### 5.2 Redaction (`_redact_body`)

0. An empty body is stored empty.
1. If the type contains `json` **or** the body starts with `{` or `[` (after leading whitespace): parse it as JSON. If that succeeds, redact recursively and re-encode compactly (`separators=(",", ":")`, `ensure_ascii=True`). If parsing fails, or parsing or redaction raises `RecursionError`, store the `unparseable_json` placeholder.
2. Else if `application/x-www-form-urlencoded`: `parse_qs(keep_blank_values=True)`, collapse single-value lists to scalars, redact, and encode as JSON. (Form bodies are stored as JSON, not as the original query string.)
3. Else: decode as UTF-8 with `errors="replace"` and store as-is (**no redaction**).

**Sensitive keys:** a key is normalized by lowercasing and removing every character outside `[a-z0-9]`. It is sensitive if the normalized key *contains* any of:

```
password, passwd, pwd, token, authorization, cookie, secret,
apikey, api_key, access_token, refresh_token, client_secret
```

(Because `_` is stripped during normalization, `api_key`, `access_token` etc. are effectively covered by `apikey` and `token`.) Matching values, including nested objects, are replaced with `"[REDACTED]"`. Lists and tuples are walked recursively. Only keys are inspected; values are never pattern-matched.

Headers are **not** logged at all, so `Authorization` and `Cookie` headers never reach Redis.

### 5.3 Truncation and compression

Applied after redaction:

1. `truncated = raw_length > MAX_BODY_BYTES`.
2. If the redacted bytes are longer than `MAX_BODY_BYTES`, cut them to `MAX_BODY_BYTES` and set `truncated = True`.
3. If they are longer than `COMPRESS_THRESHOLD_BYTES`, gzip them and set `gzip = True`.

The order is always **redact, then cut**, so a cut body can never expose a secret that redaction would have removed. For streaming responses the middleware buffers up to `MAX_CAPTURE_BYTES` (256 KB) and passes the true total via `raw_length`. If `raw_length` is larger than the captured bytes, the capture is incomplete and cannot be parsed, so the `too_large` placeholder is stored instead. This holds at most 256 KB per in-flight response in memory.

---

## 6. Caller IP and user attribution

**`get_caller_ip(request)`**: first entry of `X-Forwarded-For` (trimmed), else `request.client.host`, else `"anonymous"`. This trusts `X-Forwarded-For` unconditionally. In the new codebase, only do that behind a trusted proxy.

**`resolve_user_id(request, normalized_path, body_snapshot)`** is checked in this order:

1. *(App-specific)* Path ends with `/webhooks/dtgc/dlr` → `"system:dlr_reports"` (delivery-report webhooks grouped under a pseudo-user).
2. `request.state.user_id`, if truthy. In this app it is set by:
   - user auth → account id, or `"anonymous"`
   - machine-to-machine auth → `client_id`, or `"machine"`
   - account provisioning and the siphon routes.
3. *(App-specific)* Path contains `/siphon/`: decompress the stored request body if gzipped, parse JSON, and use `attributes.session_id`, else the top-level `session_id`. This groups every request of a call session under one id, including requests that fail before auth runs.
4. Fallback: `"anonymous"`.

**Porting note:** keep the general pattern. Auth code writes an identifier to request state, and the logger reads it *after* the handler has run. Replace steps 1 and 3 with whatever pseudo-users make sense in the new system.

---

## 7. Redis data model

All keys get `EXPIRE 259200` (3 days) on every write.

| Key | Type | Contents |
|---|---|---|
| `req:{request_id}` | Hash | Request metadata (below) |
| `req:{request_id}:body` | String (bytes) | Stored request body (may be gzip) |
| `req:{request_id}:response_body` | String (bytes) | Stored response body (may be gzip) |
| `req:all` | Sorted set | member = `request_id`, score = `ts_ms` |
| `user:{user_id}:reqs` | Sorted set | member = `request_id`, score = `ts_ms` |
| `req:metrics:{METHOD}:{route}` | Hash | `count`, `total_duration_ms`, `avg_duration_ms` (write-only, see §11). `{route}` is the matched route template, or `__unmatched__` when no route matched. `{METHOD}` is `OTHER` for non-standard methods. Both parts come from a bounded set, so random URLs cannot create new keys. |

**`req:{id}` hash fields** (all stored as strings):

| Field | Example | Notes |
|---|---|---|
| `ts` | `1759400000000` | epoch ms |
| `timestamp` | `2025-10-02T10:13:20+00:00` | ISO-8601 UTC |
| `caller_ip` | `203.0.113.7` | |
| `user_id` | `42` / `anonymous` | |
| `method` | `POST` | |
| `path` | `/api/accounts/current (login)` | normalized route template; the raw URL path (max 256 chars) when no route matched |
| `status` | `200` | |
| `duration_ms` | `37` | integer, truncated |
| `req_body_key` | `req:{id}:body` | |
| `req_body_len` | `512` | original length |
| `req_body_truncated` | `0` / `1` | |
| `req_body_gzip` | `0` / `1` | |
| `content_type` | `application/json` | request content type |
| `resp_body_key` | `req:{id}:response_body` | |
| `resp_body_len` | `2048` | |
| `resp_body_truncated` | `0` / `1` | |
| `resp_body_gzip` | `0` / `1` | |
| `resp_content_type` | `application/json` | |

### 7.1 Write path (`log_request`)

1. `await purge_expired_logs()`: no-op unless 60 s have passed since the last purge.
2. Substitute empty snapshots if either body snapshot is `None`.
3. One pipeline (redis-py's default is a `MULTI`/`EXEC` transaction):
   ```
   HSET   req:{id} <metadata>             ; EXPIRE req:{id} TTL
   SET    req:{id}:body <bytes>           ; EXPIRE ... TTL
   SET    req:{id}:response_body <bytes>  ; EXPIRE ... TTL
   ZADD   user:{uid}:reqs {id: ts_ms}     ; EXPIRE ... TTL
   ZADD   req:all {id: ts_ms}             ; EXPIRE ... TTL
   HINCRBY      req:metrics:{m}:{route} count 1
   HINCRBYFLOAT req:metrics:{m}:{route} total_duration_ms <duration>
   EXPIRE req:metrics:{m}:{route} TTL
   ```
4. Read results `[10]` (count) and `[11]` (total), then `HSET avg_duration_ms = total / count` and refresh its TTL.
5. Any exception is logged as a warning and swallowed.

### 7.2 Expiry and index pruning

Redis expires the per-request keys by itself, but **cannot expire individual sorted-set members**, and the index keys never expire while traffic keeps refreshing their TTL. Without pruning, the indexes would fill up with ids whose data is gone.

`purge_expired_logs(now_ms=None, force=False)`:

1. Unless `force` is set, return early if fewer than 60 s have passed since the last purge (monotonic clock). It is double-checked inside an `asyncio.Lock`, created lazily.
2. `cutoff = now_ms - TTL * 1000`.
3. For `req:all` and every key matching `SCAN user:*:reqs`: repeatedly `ZRANGEBYSCORE key -inf cutoff LIMIT 0 500` to collect ids, then `ZREMRANGEBYSCORE key -inf cutoff`.
4. `_delete_request_data(expired_ids)`.
5. Returns the number of ids removed.

`_delete_request_data(ids, index_key="req:all")`: `ZREM req:all ids…`, plus `ZREM index_key ids…` when it is a different key, and `DEL req:{id} req:{id}:body req:{id}:response_body` for each id. It does **not** scan the per-user indexes:

- **On purge:** step 3 has already pruned every `user:*:reqs` key by score. Each request has the same `ts_ms` score in every index, so a second scan would remove nothing.
- **Orphans in other indexes** (e.g. a metadata hash evicted under `allkeys-lru`): these are skipped on read, and pruned once their score passes the cutoff.

**Lazy repair:** a read path that finds an index member whose `req:{id}` hash is missing removes those ids from `req:all` and from the index it read, so blank entries are never returned. The list and range getters pass their index to `_build_entries(..., index_key=...)`, and the path/metrics scan removes them from the index it scans. `get_request_by_id` does no repair, because it doesn't read an index: a lookup of an unknown id costs one `HGETALL` and nothing else.

---

## 8. Read API (`RequestLogManager`)

All read methods return empty results when logging is disabled, and call `purge_expired_logs()` (throttled) before reading an index.

| Method | Redis op | Returns |
|---|---|---|
| `get_request_ids_for_all(start, end)` | `ZREVRANGE req:all` | ids, newest first |
| `get_request_ids_for_user(user_id, start, end)` | `ZREVRANGE user:{uid}:reqs` | ids |
| `get_request_ids_for_all_by_ts_range(start_ts, end_ts, start, count)` | `ZREVRANGEBYSCORE` (open bounds become ±inf) | ids |
| `get_request_ids_for_user_by_ts_range(...)` | same, per user | ids |
| `get_request_count_for_all()` / `_for_user(uid)` | `ZCARD` | int |
| `get_request_count_for_all_by_ts_range` / `_for_user_by_ts_range` | `ZCOUNT` | int |
| `get_requests_for_all` / `_for_user` / `..._by_ts_range` | ids, then `_build_entries` | list of entry dicts |
| `get_requests_matching_path(user_id, path_query, start_ts, end_ts, start, count, include_body, batch_size=500)` | scans the index in batches, pipelined `HGETALL`, case-insensitive substring filter on `path` | `(total_matches, entries)` |
| `get_request_log_metrics(user_id, path_query, start_ts, end_ts, batch_size=500)` | full scan of the index in range | metrics dict (below) |
| `get_request_by_id(request_id, include_body)` | `HGETALL` (+ `GET` bodies) | entry dict or `None` |

**`_build_entries(ids, include_body, index_key=None)`** runs one pipeline: `HGETALL` for every id, then (if `include_body`) `GET :body` for every id, then `GET :response_body` for every id. It decodes bytes, converts numeric and boolean fields (`"1"/"true"/"yes"/"y"` → `True`), and fills in `timestamp` from `ts` if it is missing. Bodies are un-gzipped (errors ignored), then parsed with `json.loads`, falling back to a UTF-8 string. Output order matches the input ids.

**Metrics output**

- `total_calls`, and `average_response_time_ms` (mean of `duration_ms`).
- `status_codes`: count per status string (`"unknown"` if the status is missing or 0).
- `endpoints`: per `(method, path)` → `count` and `avg_duration_ms`, sorted by count descending.
- `endpoint_groups`: grouped by the first path segment after `/api/` (or the first segment if there is no `/api/`, or `"root"`) → `count` and `avg_duration_ms`, sorted by count descending.

---

## 9. HTTP endpoints

All are `GET`, require an **admin user**, return **503** if logging is disabled, and return **400** if `to < from`. Naive datetimes are treated as UTC and converted to epoch ms.

### `GET /api/utils/request-logs`

| Query param | Type | Default | Notes |
|---|---|---|---|
| `user_id` | str | — | use the per-user index |
| `path` | str | — | case-insensitive substring; switches to `get_requests_matching_path` |
| `from` / `to` | ISO-8601 datetime | — | inclusive range on `ts` |
| `include_body` | bool | `false` | include decoded `body` and `response_body` |
| `page` | int ≥ 1 | 1 | |
| `limit` | 1–1000 | `DEFAULT_PAGE_LIMIT` | |
| `page_size` | 1–1000 | — | alias for `limit`; takes precedence |
| `start` | int ≥ 0 | — | absolute offset; overrides `page` |

How the query is chosen: a path filter goes to the path scan. Otherwise the index is chosen by `user_id`, and if a range is given the `_by_ts_range` variants (ZCOUNT + ZREVRANGEBYSCORE) are used; without a range it uses ZCARD + ZREVRANGE. The response is the project's standard `PaginatedResponse[RequestLogEntry]` (items, total, page, limit).

### `GET /api/utils/request-logs/metrics`

Params: `user_id`, `from`, `to`, `path`. Returns `RequestLogMetricsResponse`.

### `GET /api/utils/request-logs/{request_id}`

Param: `include_body` (default **`true`**). Returns `RequestLogEntry` or 404.

### Response schemas

```python
class RequestLogEntry(BaseModel):
    request_id: str
    ts: int
    timestamp: Optional[str] = None
    caller_ip: str
    user_id: str
    method: str
    path: str
    status: int
    duration_ms: int
    req_body_key: str
    req_body_len: int
    req_body_truncated: bool
    req_body_gzip: bool = False
    content_type: Optional[str] = None
    resp_body_key: Optional[str] = None
    resp_body_len: Optional[int] = None
    resp_body_truncated: Optional[bool] = None
    resp_body_gzip: Optional[bool] = None
    resp_content_type: Optional[str] = None
    body: Optional[Any] = None           # only with include_body
    response_body: Optional[Any] = None  # only with include_body
    model_config = ConfigDict(extra="allow")

class RequestLogEndpointMetrics(BaseModel):
    method: str
    path: str
    count: int
    avg_duration_ms: float

class RequestLogGroupMetrics(BaseModel):
    group: str
    count: int
    avg_duration_ms: float

class RequestLogMetricsResponse(BaseModel):
    total_calls: int
    average_response_time_ms: float
    status_codes: dict[str, int] = {}
    endpoints: list[RequestLogEndpointMetrics] = []
    endpoint_groups: list[RequestLogGroupMetrics] = []
```

---

## 10. Porting checklist

**Core (framework-agnostic)**

- [ ] Async Redis client, created at startup with `decode_responses=False`; the feature must degrade to a no-op without Redis.
- [ ] Middleware: request id + timestamp, request body snapshot *before* the handler, timing, response capture (buffered **and** streaming), schedule the write *after* the handler.
- [ ] Make sure reading the request body in middleware does not consume it for the handler (Starlette caches `request.body()`; other frameworks may need buffering).
- [ ] The write is fire-and-forget and never raises into the request path.
- [ ] Content-type classification, redaction, truncation, gzip exactly as in §5.
- [ ] Redis keys, TTLs and pipeline as in §7.1.
- [ ] Background purge loop plus throttled opportunistic purge (§7.2).
- [ ] Lazy deletion of orphaned index members on read.
- [ ] Admin-only list / metrics / detail endpoints (§9).

**Integration points to adapt**

- [ ] Where auth stores the user id on the request (`request.state.user_id` here).
- [ ] Pseudo-users for unauthenticated traffic (DLR webhook, siphon `session_id`), or drop them.
- [ ] The `/api/accounts/current (login)` label: drop it or replace it.
- [ ] Optional: the DB query-logging context (`set_query_request_context`).
- [ ] Trusted-proxy handling for `X-Forwarded-For`.
- [ ] Your own pagination envelope and admin authorization dependency.

**Tests to bring over** (`test_request_logging.py` uses a fake Redis/pipeline):

- [ ] Write a request, then read it back through both `_build_entries` and `get_request_by_id`; verify metadata and gzip/JSON body decoding.
- [ ] An index member whose hash is missing is removed from the index it was read from, and `None`/empty is returned. An unknown id passed to `get_request_by_id` triggers no repair and no `SCAN`.
- [ ] A streamed JSON response between 32 KB and 256 KB is redacted before it is cut. Longer streams, malformed JSON and very deeply nested bodies are stored as placeholders and never raise.
- [ ] Unmatched routes and unknown methods produce `req:metrics:OTHER:__unmatched__`-style keys, never raw URLs.

---

## 11. Known issues and suggested improvements

Consider fixing these when porting rather than copying them.

1. **Route template is probably not resolved.** The middleware reads `request.scope["route"]` *before* `call_next`, but FastAPI only sets it during routing, so `endpoint` usually falls back to the raw URL (`/api/users/123`). As a result, `normalize_path` rarely applies, path filters and endpoint metrics are keyed by concrete URLs, and `req:metrics:*` keys multiply with every distinct id. **Fix:** read the route template *after* `call_next` (from `request.scope`), or use a framework hook that exposes the matched route. *(This codebase reads it after `call_next`. Requests that match no route use `__unmatched__` in the metrics key, so scanners cannot create unlimited keys; see §7.)*
2. **`req:metrics:*` hashes are never read.** The metrics endpoint recomputes everything from per-request hashes. Either drop these writes or build the metrics endpoint on top of them.
3. **Metrics and path search are O(N) over the range.** Both scan every request in range with `HGETALL`. For high traffic, consider a secondary index per path (`path:{method}:{template}` sorted set), or ship logs to a store built for querying (ClickHouse, Loki, OpenSearch).
4. **`SCAN user:*:reqs` on every purge.** *(Partly fixed: deletes and read-path repair no longer scan, see §7.2.)* The periodic purge still scans every user index once per minute, so its cost grows with the number of distinct users. To remove it, store `user_id` alongside the id in `req:all` (e.g. member `"{uid}|{id}"`) or keep a set of active user ids.
5. **Truncation can break JSON.** Redaction runs before truncation, so a body cut at 32 KB is no longer valid JSON and is returned as a string. Acceptable, but document it in the UI. Bodies that cannot be redacted at all are stored as placeholders instead (§5.1).
6. **Non-JSON, non-form text bodies are not redacted** (XML, plain text, GraphQL). Add redaction there if those bodies may carry secrets.
7. **Interrupted streams are never logged.** If the client disconnects or the stream errors mid-way, the wrapper generator never reaches the log call. Wrap it in `try/finally` to log a partial record.
8. **Untracked background tasks.** `asyncio.create_task` results are not referenced, so they can be garbage-collected mid-flight and pending writes are lost on shutdown. Keep them in a set and await them on shutdown, or use a bounded queue with a worker.
9. **`X-Forwarded-For` is trusted unconditionally**, so the caller IP can be spoofed.
10. **`duration_ms` excludes body streaming.** It is measured when `call_next` returns, which under `BaseHTTPMiddleware` is when the response headers arrive. For normal JSON responses that is effectively the full handler time; for true streaming responses it is only time-to-first-byte.
11. **Duplicated decoding logic.** `_build_entries` and `get_request_by_id` repeat the metadata/body decoding; factor it into one helper in the port.

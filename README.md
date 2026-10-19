# core-crewsim

FastAPI service for the crewsim admin API.

See [Architecture](docs/architecture.md) for the source layout, dependency rules, and guidance on
adding a domain.

## Local development with UV

[UV](https://docs.astral.sh/uv/) is the primary package manager for this project. Bootstrap it
in a Python virtual environment, then use UV for project dependency management:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install uv
uv sync --active --extra dev
```

On Windows, activate the environment with `venv\Scripts\activate` instead. The `--active` flag
tells UV to install the locked dependencies into the activated `venv` environment.

Copy the development environment template before running commands that connect to PostgreSQL:

```bash
cp .env.example .env
```

The template uses `DB_HOST=db` for Compose. When running the application, migrations, or seed
command directly on the host, set `DB_HOST=localhost` in `.env` (or in the command environment).

Apply migrations and start the local API with:

```bash
uv run --active alembic upgrade head
uv run --active uvicorn app.main:app --reload --no-proxy-headers
```

The API is available at `http://localhost:8000`, with interactive documentation at
`http://localhost:8000/docs`.

## Run with Docker Compose

The Compose stack runs four services:

- `db`: PostgreSQL with data stored in the `postgres_data` named volume.
- `migrate`: a one-shot job that applies all Alembic migrations.
- `api`: the FastAPI application, started only after the database is healthy and migrations
  complete successfully.
- `pgadmin`: a local pgAdmin UI, available on `http://localhost:5051` by default.

Docker with the Compose plugin is required. Copy the development defaults and start the stack:

```bash
cp .env.example .env
docker compose up --build --wait
```

The API is available at `http://localhost:8000`. Check it with:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/
```

The interactive API documentation is at `http://localhost:8000/docs`.

### Seed data for frontend testing

After the database migrations have completed, create 100 deterministic user/eSIM pairs,
300 linked usage events, and 100 linked Stripe notifications. The fixtures include varied
profile, device, status, balance, date, network, data, voice, SMS, payment, tax, and credit
values to exercise pagination and information-dense tables:

```bash
docker compose exec api python -m app.seed
```

The command is safe to run more than once: existing seed users, eSIMs, usage events, and Stripe
notifications are left unchanged. Use `--count` to create between 1 and 100 pairs (with three
usage events and one Stripe notification per pair) instead of the default 100:

```bash
docker compose exec api python -m app.seed --count 25
```

When running the API directly rather than through Compose, use:

```bash
uv run --active python -m app.seed
```

The script reads the normal `DB_*` application configuration (or the optional
`DATABASE_URL` override).

### Common commands

```bash
# Show service and health status
docker compose ps

# Follow API logs
docker compose logs --follow api

# Check the current database revision
docker compose exec api alembic current

# Apply migrations again after adding a revision
docker compose run --rm migrate

# Stop containers while preserving database data
docker compose down
```

To intentionally remove the local database as well, run `docker compose down --volumes`.
This permanently deletes the Compose-managed PostgreSQL volume.

## Database migrations

Alembic configuration lives in `alembic.ini`, and migration scripts live in `migrations/`.
With the development environment active and database settings configured, use:

```bash
# Show the revision history and current migration heads
uv run --active alembic history
uv run --active alembic heads

# Apply all pending migrations
uv run --active alembic upgrade head

# Confirm that the SQLAlchemy models require no new migration
uv run --active alembic check
```

To generate a migration after an intentional model change, run:

```bash
uv run --active alembic revision --autogenerate -m "describe the change"
```

Review generated migrations before applying them. Model discovery is configured in
`migrations/env.py`; a new domain model must be imported there.

The `timezone` domain maps to `time_zone` (`name TEXT PRIMARY KEY`,
`created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`). Its migration automatically seeds
IANA timezone identifiers, including aliases and `UTC`, from PostgreSQL's
`pg_timezone_names` catalog, excluding host-local entries and `posix/` and `right/`
duplicates. The seeded identifiers reflect the database server's installed timezone
data when the migration runs; no separate development seed command is needed.

## Configuration

Compose reads development settings from `.env`. It defaults `DB_HOST` to the container-safe
hostname `db`; `localhost` would incorrectly refer to the API container itself.

The database configuration is assembled at runtime from `DB_HOST`, `DB_PORT`, `DB_DATABASE`,
`DB_USERNAME`, and `DB_PASSWORD`. In Dokploy, set all five on the application as runtime
environment variables. The credentials in `.env.example` are local development defaults;
supply production values through Dokploy's environment or secret manager, and do not copy
`.env` into the image. `DATABASE_URL` remains available as an optional override and takes
precedence when it is set.

`APP_PORT` controls the host port. The application always listens on port `8000` inside the
container.

### Browser access and Cloudflare Access

Set `CORS_ORIGINS` to a comma-separated list of exact frontend origins. For production, use:

```dotenv
CORS_ORIGINS=https://bss.crewsim.dev
```

Do not include paths or a trailing slash. The API accepts cross-origin `GET`, `POST`, `PATCH`,
`DELETE`, and `OPTIONS` requests, and permits the `Content-Type`, `CF-Access-Client-Id`, and
`CF-Access-Client-Secret` request headers.

The Cloudflare Access application for `core.crewsim.dev` must also be configured separately:

1. Add a **Service Auth** policy whose include rule matches the intended service token.
2. Enable **Bypass OPTIONS requests to origin** so browser preflight requests reach this API.
3. Keep the service-token values in deployment secrets; never commit them to this repository.

Access policy and preflight settings are Cloudflare account configuration and are not controlled
by this FastAPI application.

> [!WARNING]
> A browser bundle cannot keep `CF-Access-Client-Secret` confidential. If the frontend runs in
> users' browsers, inject the service-token headers in a trusted server-side proxy or Cloudflare
> Worker instead of exposing the token in frontend code.

### Caller IP in request logs

`caller_ip` is the first globally reachable IP found, reported rather than verified. Candidates are
checked in this order (each with its source in `caller_ip_source` and `client_ip_candidates`):
`CF-Connecting-IPv6`, `CF-Connecting-IP`, `True-Client-IP`, `Fastly-Client-IP`,
`CloudFront-Viewer-Address`, `X-Azure-ClientIP`, `X-Azure-SocketIP`, `X-Envoy-External-Address`,
`Forwarded`, `X-Forwarded-For`, `X-Original-Forwarded-For`, `X-Real-IP`, `X-Client-IP`,
`Client-IP`, `X-Cluster-Client-IP`, then the socket address.

Private, loopback, link-local, shared, reserved, multicast, and malformed values are skipped. If
nothing public remains, `caller_ip` is empty. Header values can be spoofed, so never use
`caller_ip` for access control. Uvicorn runs with `--no-proxy-headers` so the socket address is the
real connection peer; check HTTPS redirects after deploying behind a proxy.

### Telcovision account refresh

`POST /api/accounts/refresh` synchronizes local accounts with the Telcovision reseller account
list. Set these provider values as deployment secrets (for example in Dokploy); never commit them
or bake them into the image:

- `TELCOVISION_API_URL`: Telcovision API base URL.
- `TELCOVISION_API_TOKEN`: provider API token. It is used only by the server and must never
  appear in a trigger command or URL.

The `ACCOUNTS_REFRESH_KEY` setting and `X-Accounts-Refresh-Key` check exist, but the route's key
check is currently disabled. Trigger a refresh with any Cloudflare Access headers your deployment
requires:

```bash
curl --request POST \
  https://core.crewsim.dev/api/accounts/refresh
```

The operation is synchronous: the request returns only after the provider call and database
changes finish. A successful `200` response reports the committed `fetched`, `created`,
`updated`, `unchanged`, and `deleted` account counts. Error responses carry a generic `detail`
and never include provider details or secrets:

| Status | Meaning |
| ------ | ------- |
| 409 | Another refresh is already running. Retry after it completes. |
| 502 | Telcovision failed, timed out, or returned a malformed or unsuccessful response. No rows were changed. The body is `{"detail": {"message", "category", "provider_code"}}`. |
| 503 | `TELCOVISION_API_URL` or `TELCOVISION_API_TOKEN` is not configured. |

> [!WARNING]
> The refresh treats the provider response as the complete account list. Local account IDs that
> are absent from it are **deleted**. eSIMs retain their `account_id` and
> `use_account_for_charging` values, even when the referenced account no longer exists. An empty
> successful response therefore deletes every account without changing eSIMs. Apply migration
> `c9e6f4a2b718` before deploying this refresh behavior, and review the token's visibility and
> production account IDs before enabling the trigger.

#### Outbound API log inspection

Every account refresh fetches a live Telcovision response. The outbound call appears as its own
item in `GET /api/utils/request-logs`, with `direction: "outbound"`, its own `request_id`, and a
redacted `url` (also searchable through the `path` filter). It has no parent refresh-request link.
Both the list endpoint and `GET /api/utils/request-logs/{request_id}` include captured bodies by
default for inbound and outbound entries: `body` is the request body, and `response_body` is the
response body. Pass `include_body=false` to skip loading body content. The detail endpoint also
shows the HTTP status and duration. These endpoints currently have no application-level access
check. Older nested `outbound` records remain readable until they expire, but new calls are stored
as separate items.

The token and other sensitive query or structured-body values are redacted before storage.
Inbound request and response bodies have a 32 KiB storage cap; binary and multipart bodies are
omitted. Inbound plain text and XML are not redacted. Outbound JSON and form request and response
bodies are stored up to 5 MiB each; larger, unreadable, malformed, or unsupported bodies become
an omission marker with a reason and byte count. Existing standalone outbound entries are not
backfilled, so their top-level `body` field remains empty. Redis keeps each item for up to three
days. Logging does not serve responses back to account refreshes, and Redis failures do not fail
the refresh. Logging is disabled when `REDIS_HOST` is empty. The Compose Redis instance has no
disk persistence and may evict records before their three-day TTL.

Logger `app.integrations.telcovision.*` records the shared `request_id`, operation, host/path,
duration, HTTP status, and failure category without response bodies or the token-bearing URL.
The `httpx` logger is held at `WARNING` because it prints the token-bearing URL at `INFO`.
New outbound integrations should use `logged_request` or `logged_async_request` from
`app/integrations/outbound_http.py` and pass the inbound request ID and exchange collector so
their calls can be captured as independent API log items.

Because accounts are now managed by the refresh, the account create (`POST`), update (`PATCH`),
and delete (`DELETE`) routes return `409`. Account and eSIM read routes are unchanged.

### Telcovision subscriber refresh

`POST /api/esims/refresh/{account_id}` synchronizes one Telcovision account's subscribers into
local eSIMs. The existing `POST /api/esims/refresh?account_id=<account_id>` form is also supported
and uses the same refresh pipeline. Neither form requires a request body. `account_id` must be
a positive integer identifying an existing local account. For example:

```bash
curl -X POST http://localhost:8000/api/esims/refresh/123
```

The request uses the existing `TELCOVISION_API_URL` and `TELCOVISION_API_TOKEN`
settings, sends `{"listSubscriber": {"accountId": "<account_id>"}}` to Telcovision, and
commits all inserts and updates in one transaction. It returns a `list[ESIMRefreshResult]`
containing the persisted eSIM values in snapshot order.

Apply migration `a2f7c9d4e681` before using this pipeline. It adds `uq_esims_imsi` and stops with
resolution instructions if existing records share an IMSI. Resolve those duplicates explicitly
and rerun the migration; it never deletes or merges records. Use the migration commands in
the local development or Compose instructions above.

Invoke the synchronous callable from an internal Python caller with a dedicated database
session:

```python
from uuid import uuid4

from app.config import get_settings
from app.database import SessionLocal
from app.integrations.redis.outbound_logging import OutboundExchange
from app.integrations.telcovision.subscribers import refresh_telcovision_subscribers

exchanges: list[OutboundExchange] = []
account_id = ...
with SessionLocal() as session:
    results = refresh_telcovision_subscribers(
        session,
        get_settings(),
        account_id=account_id,
        request_id=uuid4().hex,
        outbound_exchanges=exchanges,
    )
```

When invoking it from a request handler, pass `request.state.request_id` and
`request.state.outbound_exchanges` so the existing middleware persists the outbound exchange.
In the standalone example, exchanges remain in the caller's in-memory list.

Both forms return 422 when `account_id` is zero, negative, or not an integer. The query form
also returns 422 when `account_id` is missing. Both return 404 when the account does not exist
locally; 502 for Telcovision transport, provider, or response errors; and 503 when Telcovision
configuration is missing. Neither form has a refresh key.

Each `imsiList[].imsi` produces one eSIM snapshot. The pipeline matches local records by IMSI
and updates these fields:

| Telcovision value | eSIM attribute |
| ----------------- | -------------- |
| `imsiList[].imsi` | `imsi` (synchronization key) |
| `accountId` | `accountid` (`account_id` in results) |
| `sim.esim` | `isesim` |
| `balance` | `balance` |
| `useAccountForCharging` | `use_account_for_charging` |
| `sim.smdpServer` | `smdpserver` |
| `sim.activationCode` | `activationcode` |
| `allowedData` | `allow_data` |
| `mobilePlanId` | `mobileplanid` |
| `activationDate` | `activationdate` |
| `lastUsageDate` | `lastusagedate` |
| `status[].status` for the highest numeric `status[].id` | `subscriber_status` |

New eSIMs receive a generated local numeric ID, `userid=None`, and a random seven-character
token containing lowercase ASCII letters and digits. Existing records keep their user,
token, name, and unrelated device/network fields. Missing nullable provider values clear the
corresponding mapped fields; an empty status history sets `subscriber_status=None`. Local
IMSIs absent from the response are left alone, and a valid empty subscriber list changes
nothing. No eSIMs are deleted. Account IDs can be stored before their accounts are refreshed.

Pagination is deferred: `hasMore: true` or an `nbFound` value that differs from the subscriber
list length raises `TelcovisionError("incomplete_response")` before any writes. Duplicate IMSIs
raise `TelcovisionError("duplicate_imsi")`; malformed records raise
`TelcovisionError("invalid_response")`. Fetch, parsing, and persistence failures roll back the
refresh; database integrity failures become `ResourceConflictError`. The bounded HTTP client
closes on success or failure. Run subscriber refreshes sequentially; refresh locking is deferred.

## Build and run the API image directly

When PostgreSQL is managed separately, build the same image and pass a database URL reachable
from inside the container:

```bash
docker build --tag core-crewsim:local .
docker run --rm \
  --publish 8000:8000 \
  --env APP_ENV=production \
  --env APP_DEBUG=false \
  --env DB_HOST=database \
  --env DB_PORT=5432 \
  --env DB_DATABASE=core_crewsim \
  --env DB_USERNAME=user \
  --env DB_PASSWORD=password \
  core-crewsim:local
```

The container runs `alembic upgrade head` before starting Uvicorn. If a migration fails, the API
does not start and the container exits with a failure. This startup approach is intended for a
single API replica, such as a Dockerfile-based Dokploy application.

For deployments with multiple API replicas, run migrations as a separate deployment step to
avoid concurrent migration attempts:

```bash
docker run --rm \
  --env DB_HOST=database \
  --env DB_PORT=5432 \
  --env DB_DATABASE=core_crewsim \
  --env DB_USERNAME=user \
  --env DB_PASSWORD=password \
  core-crewsim:local alembic upgrade head
```

## Dependency updates

Use UV to add, update, and remove dependencies so that `pyproject.toml` and `uv.lock` stay in
sync. For example:

```bash
uv add <package>
uv add --dev <package>
uv remove <package>
uv lock --upgrade
```

The runtime image installs exact versions from `requirements.lock`. Regenerate that file with
UV whenever runtime dependencies change:

```bash
uv export --format requirements-txt --no-dev --no-emit-project --output-file requirements.lock
```

Review and test dependency changes before rebuilding the image. Use `pip` only for the initial
UV bootstrap; manage project packages with UV after that.

## Development checks

```bash
# Run lint checks
uv run --active ruff check .

# Build and inspect production package artifacts
uv build
```

## TODOs

- Add pre-commit hooks and other development tooling.
- Add a CI/CD pipeline after choosing a deployment platform.

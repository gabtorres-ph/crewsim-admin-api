# Core CrewSim

Backend for the CrewSim admin app. Manages users, accounts, eSIMs, packages, and usage.
Syncs accounts and eSIMs from Telcovision, the mobile service provider.

## Quick start

Requires Docker with Compose. Run from the project folder:

```bash
cp .env.example .env
docker compose up --build --wait
```

This starts the API, database, request logging, and database viewer. Database updates run automatically.

| Open | Purpose |
| --- | --- |
| [API docs](http://localhost:8000/docs) | Browse and try API requests |
| [Health check](http://localhost:8000/health) | Confirm the API is running |
| [Database viewer](http://localhost:5051) | Inspect data; login: `admin@example.com` / `admin` |

## Sample data

Create test users, eSIMs, usage, and payment notifications:

```bash
docker compose exec api python -m app.seed
```

Safe to repeat. Add `--count 25` for a smaller dataset (default: 100 users and eSIMs).

## Common commands

| Task | Command |
| --- | --- |
| Check services | `docker compose ps` |
| View API logs | `docker compose logs --follow api` |
| Apply database updates | `docker compose run --rm migrate` |
| Stop; keep data | `docker compose down` |

## Run Python locally

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and PostgreSQL.
Start the database with Compose:

```bash
cp .env.example .env
docker compose up -d db
```

In `.env`, set `DB_HOST=localhost`, `DB_PORT=5433`, and `REDIS_HOST=` (disables request logging).
Then run:

```bash
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --no-proxy-headers
```

Run lint checks with `uv run ruff check .`.

## Sync provider data

Set `TELCOVISION_API_URL` and `TELCOVISION_API_TOKEN` in `.env` before starting the API.
Use the API docs to send these requests:

| Request | Effect |
| --- | --- |
| `POST /api/accounts/refresh` | Sync all accounts; **delete local accounts missing from the provider** |
| `POST /api/esims/refresh/{account_id}` | Add or update one account's eSIMs; keep missing eSIMs |
| `POST /api/esims/{imsi}/refresh` | Refresh an existing eSIM from Telcovision's `getSingleSubscriber` response |
| `POST /api/esims/move-to-account` | Move selected eSIMs between accounts in Telcovision, then update CrewSim |

Refresh accounts first, then refresh eSIMs using an existing account ID.
The eSIM route also accepts `POST /api/esims/refresh?account_id=123`. Neither form needs a body.
The single eSIM refresh route takes a 5–15 digit IMSI and needs no body. Fields omitted by
Telcovision keep their existing database values; an unknown local IMSI returns 404.
Refresh routes currently have no application-level access check.

### Move eSIMs between accounts

Send a source account, destination account, and one or more IMSIs:

```json
{
  "source_account_id": 10,
  "destination_account_id": 15,
  "imsis": ["200010416000001", "200010416000003"]
}
```

The accounts must differ, every IMSI must currently belong to the source account in CrewSim, and
Telcovision permits moves only between accounts of the same reseller. CrewSim sends one provider
request per IMSI so it never includes unrequested subscribers in a provider range. A successful
request returns the moved IMSIs with their destination account IDs.

Each confirmed move commits separately. If a later provider request fails, previously completed
moves remain committed and the 502 response identifies `moved_imsis`, `failed_imsi`, and
`not_attempted_imsis`. Before retrying an interrupted or timed-out transfer, refresh each affected
eSIM with `POST /api/esims/{imsi}/refresh` to reconcile CrewSim with Telcovision, then retry only
the IMSIs still assigned to the source account.

## Deployment settings

See [.env.example](.env.example) for settings. Supply production database credentials and provider
secrets through your deployment platform. Keep secrets out of source code and browser apps.
Set `CORS_ORIGINS` to allowed frontend URLs, without paths or trailing slashes.

The Docker image applies database updates before starting. With multiple API instances,
run updates once as a separate deployment step.

## Technical reference

- [Code structure and adding features](docs/architecture.md)
- [Request logging](docs/request-logging.md)

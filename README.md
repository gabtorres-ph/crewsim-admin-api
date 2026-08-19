# core-crewsim

FastAPI service for the crewsim admin API.

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

## Run with Docker Compose

The Compose stack runs three services:

- `db`: PostgreSQL with data stored in the `postgres_data` named volume.
- `migrate`: a one-shot job that applies all Alembic migrations.
- `api`: the FastAPI application, started only after the database is healthy and migrations
  complete successfully.

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

After the database migrations have completed, create eight deterministic user/eSIM pairs:

```bash
docker compose exec api python -m app.seed
```

The command is safe to run more than once: existing seed users and eSIMs are left unchanged.
Use `--count` to create between 5 and 10 pairs instead of the default eight:

```bash
docker compose exec api python -m app.seed --count 10
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
uv run --active pytest
uv run --active ruff check .
```

## TODOs

- Add pre-commit hooks and other development tooling.
- Add a CI/CD pipeline after choosing a deployment platform.

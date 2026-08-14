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

Compose reads development settings from `.env`. The application receives a container-safe
`DATABASE_URL` using `db` as the hostname; `localhost` would incorrectly refer to the API
container itself.

The credentials in `.env.example` are local development defaults. Supply production values
through the deployment platform's environment or secret manager, and do not copy `.env` into
the image.

`APP_PORT` controls the host port. The application always listens on port `8000` inside the
container.

## Build and run the API image directly

When PostgreSQL is managed separately, build the same image and pass a database URL reachable
from inside the container:

```bash
docker build --tag core-crewsim:local .
docker run --rm \
  --publish 8000:8000 \
  --env APP_ENV=production \
  --env APP_DEBUG=false \
  --env DATABASE_URL=postgresql+psycopg://user:password@database:5432/core_crewsim \
  core-crewsim:local
```

Run migrations as a separate deployment step before starting replicated API containers:

```bash
docker run --rm \
  --env DATABASE_URL=postgresql+psycopg://user:password@database:5432/core_crewsim \
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

# core-crewsim

FastAPI service for the crewsim admin API.

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

The runtime image installs exact versions from `requirements.lock`. Regenerate it whenever
the project dependencies change:

```bash
python -m pip install pip-tools
pip-compile --strip-extras --output-file=requirements.lock pyproject.toml
```

Review and test dependency changes before rebuilding the image.

## Development checks

```bash
pytest
ruff check .
```

## TODOs

- Add pre-commit hooks and other development tooling.
- Add a CI/CD pipeline after choosing a deployment platform.

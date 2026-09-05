# Core CrewSim Architecture

Core CrewSim is organized as a vertical-domain FastAPI application. Each business domain owns
its HTTP routes, request and response schemas, business rules, persistence operations, database
models, and tests. Shared application infrastructure remains at the top of `app/` or in
`app/common/`.

## Source tree

```text
core-crewsim/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Application composition and root/health routes
│   ├── routes.py                  # Central /api router registry
│   ├── config.py                  # Environment-backed settings
│   ├── database.py                # Engine, session factory, Base, and get_db
│   ├── seed.py                    # Development seed CLI
│   ├── common/
│   │   ├── __init__.py
│   │   ├── cors.py
│   │   ├── exceptions.py
│   │   ├── manager.py         # Shared transaction behavior
│   │   ├── resource_access.py # Shared CRUD persistence behavior
│   │   └── test_cors.py
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── resource_access.py
│   │   ├── manager.py
│   │   ├── routes.py
│   │   └── test_accounts.py
│   ├── users/                      # Same domain file layout
│   ├── esims/                      # Same domain file layout
│   ├── favorites/                  # Same domain file layout
│   ├── test_architecture.py
│   ├── test_config.py
│   ├── test_main.py
│   └── test_seed.py
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── docs/
│   ├── architecture.md
│   └── architecture-reorganization-plan.md
├── conftest.py                         # Shared pytest fixtures
├── Dockerfile
├── compose.yaml
├── alembic.ini
├── pyproject.toml
└── README.md
```

Tests are colocated with the application component they exercise. Build and Docker exclusions
keep `test_*.py` and the root `conftest.py` out of production artifacts.

## Dependency rules

Within a domain, dependencies point inward toward persistence and models:

```text
routes → manager → resource_access → models
   └───────── schemas ←──────────┘
```

- Routes handle HTTP concerns and depend on schemas and managers. They do not query SQLAlchemy
  sessions directly.
- Managers contain business validation and own transaction boundaries. Shared write/rollback
  behavior comes from `app.common.manager.TransactionalManager`.
- Resource-access classes own SQLAlchemy queries and persistence operations. Common CRUD behavior
  comes from `app.common.resource_access.CRUDResourceAccess`.
- Models contain SQLAlchemy mappings and relationship declarations only.
- Schemas define the public request and response shapes, including aliases between API field names
  and existing database attribute names.
- A domain never imports another domain's routes. Cross-domain validation may explicitly use the
  other domain's manager or resource-access class.
- Modules in `app/common/` do not import concrete business domains.

`app/main.py` is the composition root. It configures FastAPI, CORS, exception handlers, the API
prefix, and the non-API `/` and `/health` endpoints. `app/routes.py` is the sole central registry
for domain routers. Domain routers never hard-code the global `/api` prefix.

Nested endpoints live in the domain that owns the resource returned by the endpoint, even when
the URL begins with a different resource. For example, the eSIM domain owns
`/users/{user_id}/esims` and `/accounts/{account_id}/esims`, while the favorites domain owns
`/users/{user_id}/favorites`. Separate routers may be used to preserve the parent resource's
OpenAPI tag.

All domain model modules must be imported before using `Base.metadata` for schema creation or
migration comparison. Alembic does this in `migrations/env.py`, and pytest does it in the root
`conftest.py`.

## Adding a domain

Create `app/<domain>/` with these files:

- `__init__.py`
- `models.py`
- `schemas.py`
- `resource_access.py`
- `manager.py`
- `routes.py`
- `test_<domain>.py`

Keep each layer within the dependency direction above. Register the domain router in
`app/routes.py`, and import its model module in both `migrations/env.py` and `conftest.py` so
Alembic and tests see its tables. Put nested routes in this package when the new domain owns the
resource they return. Add application-level tests only when behavior belongs to composition,
configuration, seeding, or an architecture rule rather than to one domain.

When an external service is introduced, place its adapter in `app/integrations/<provider>/` and
keep provider-specific details out of domain modules. When a distinct API surface is introduced,
place it in its own `app/<api_name>/` package and compose it explicitly. These are conventions for
future capabilities; no integration or alternate API package exists today.

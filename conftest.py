import os

import anyio.to_thread
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session

from app.accounts import models as account_models  # noqa: F401
from app.config import get_settings
from app.crew import models as crew_models  # noqa: F401
from app.currencies import models as currency_models  # noqa: F401
from app.database import Base, get_db
from app.esims import models as esim_models  # noqa: F401
from app.favorites import models as favorite_models  # noqa: F401
from app.language import models as language_models  # noqa: F401
from app.main import app
from app.packages import models as package_models  # noqa: F401
from app.sim_notifications import models as sim_notification_models  # noqa: F401
from app.sms import models as sms_models  # noqa: F401
from app.timezone import models as timezone_models  # noqa: F401
from app.usage import models as usage_models  # noqa: F401
from app.users import models as user_models  # noqa: F401


def _test_database_url():
    settings = get_settings()
    url = make_url(settings.test_database_url)
    # pytest-xdist workers each get their own database so schema setup cannot collide.
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    if worker:
        url = url.set(database=f"{url.database}_{worker}")
    if url.database == make_url(settings.database_url).database:
        raise RuntimeError(
            "TEST_DATABASE_URL must name a different database than DATABASE_URL; "
            "the test suite drops and recreates every table in it."
        )
    return url


def _ensure_database_exists(url) -> None:
    admin_engine = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", pool_pre_ping=True
    )
    try:
        with admin_engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
            )
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def db_engine() -> Engine:
    url = _test_database_url()
    _ensure_database_exists(url)
    engine = create_engine(url)
    # Start from a clean schema in case a previous run was interrupted.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_connection(db_engine: Engine):
    """Yield a connection whose outer transaction is rolled back after each test."""
    with db_engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


@pytest.fixture(scope="function")
def db_session(db_connection) -> Session:
    # Commits inside code under test release a SAVEPOINT; the outer transaction still rolls
    # back, so every test sees an empty database.
    with Session(
        bind=db_connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: Session, monkeypatch):
    async def run_sync_inline(function, *args, **kwargs):
        return function(*args)

    # The sandbox used by the test runner cannot start AnyIO worker threads. Running
    # synchronous route/dependency callables inline keeps ASGI tests deterministic.
    monkeypatch.setattr(anyio.to_thread, "run_sync", run_sync_inline)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()

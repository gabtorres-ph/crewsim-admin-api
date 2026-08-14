import anyio.to_thread
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture(scope="function")
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with test_session_factory() as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


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

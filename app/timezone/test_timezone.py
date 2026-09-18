import importlib

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.timezone.models import Timezone


def test_timezone_defaults_and_unique_name(db_session: Session) -> None:
    timezone = Timezone(name="Asia/Manila")
    db_session.add(timezone)
    db_session.commit()

    assert db_session.get(Timezone, "Asia/Manila") is timezone
    assert timezone.created_at is not None

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(text("INSERT INTO time_zone (name) VALUES ('Asia/Manila')"))
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(text("INSERT INTO time_zone (name, created_at) VALUES ('UTC', NULL)"))


def test_migration_seeds_identifiers_and_can_be_reapplied() -> None:
    migration = importlib.import_module("migrations.versions.6d2e8f4a9c10_add_time_zone_table")
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.begin() as connection:
            # Stand in for the PostgreSQL catalog in the SQLite test environment.
            connection.execute(text("CREATE TABLE pg_timezone_names (name TEXT)"))
            identifiers = {"UTC", "Asia/Manila", "America/New_York", "US/Eastern", "Etc/GMT+5"}
            excluded = {"localtime", "posixrules", "posix/UTC", "right/UTC"}
            connection.execute(
                text("INSERT INTO pg_timezone_names (name) VALUES (:name)"),
                [{"name": name} for name in sorted(identifiers | excluded)],
            )
            with Operations.context(MigrationContext.configure(connection)):
                for _ in range(2):
                    migration.upgrade()
                    rows = connection.execute(select(Timezone.name, Timezone.created_at)).all()
                    assert {row.name for row in rows} == identifiers
                    assert all(row.created_at is not None for row in rows)
                    migration.downgrade()
                    assert not inspect(connection).has_table("time_zone")
    finally:
        engine.dispose()

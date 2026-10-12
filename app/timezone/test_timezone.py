import importlib

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Connection, inspect, select, text
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


def test_migration_seeds_identifiers_and_can_be_reapplied(db_connection: Connection) -> None:
    migration = importlib.import_module("migrations.versions.6d2e8f4a9c10_add_time_zone_table")
    # The session schema already has time_zone; PostgreSQL DDL is transactional, so dropping it
    # here is undone by the fixture's rollback.
    db_connection.execute(text("DROP TABLE time_zone"))
    catalog = set(db_connection.scalars(text("SELECT name FROM pg_timezone_names")))
    identifiers = {
        name
        for name in catalog
        if not name.startswith(("posix/", "right/")) and name not in {"localtime", "posixrules"}
    }
    assert {"UTC", "Asia/Manila", "America/New_York"} <= identifiers

    with Operations.context(MigrationContext.configure(db_connection)):
        for _ in range(2):
            migration.upgrade()
            rows = db_connection.execute(select(Timezone.name, Timezone.created_at)).all()
            assert {row.name for row in rows} == identifiers
            assert all(row.created_at is not None for row in rows)
            migration.downgrade()
            assert not inspect(db_connection).has_table("time_zone")

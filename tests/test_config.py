import pytest

from app.config import Settings


def test_database_url_is_built_from_db_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_HOST", "postgres.internal")
    monkeypatch.setenv("DB_PORT", "6543")
    monkeypatch.setenv("DB_DATABASE", "crew sim")
    monkeypatch.setenv("DB_USERNAME", "app@user")
    monkeypatch.setenv("DB_PASSWORD", "p@ss/word")

    settings = Settings(_env_file=None)

    assert settings.database_url == (
        "postgresql+psycopg://app%40user:p%40ss%2Fword@postgres.internal:6543/crew%20sim"
    )


def test_database_url_override_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    override = "postgresql+psycopg://override:secret@database:5432/crewsim"
    monkeypatch.setenv("DATABASE_URL", override)
    monkeypatch.setenv("DB_HOST", "ignored")
    monkeypatch.setenv("DB_DATABASE", "ignored")
    monkeypatch.setenv("DB_USERNAME", "ignored")
    monkeypatch.setenv("DB_PASSWORD", "ignored")

    settings = Settings(_env_file=None)

    assert settings.database_url == override


def test_cors_origins_are_trimmed_and_empty_values_are_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://bss.crewsim.dev, http://localhost:5173,",
    )

    settings = Settings(_env_file=None)

    assert settings.allowed_cors_origins == [
        "https://bss.crewsim.dev",
        "http://localhost:5173",
    ]

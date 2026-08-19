from functools import lru_cache
from urllib.parse import quote

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "core-crewsim"
    app_env: str = "development"
    app_debug: bool = True
    api_prefix: str = "/api"
    database_url: str = Field(default="", alias="DATABASE_URL")
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT", ge=1, le=65535)
    db_database: str = Field(default="core_crewsim", alias="DB_DATABASE")
    db_username: str = Field(default="postgres", alias="DB_USERNAME")
    db_password: str = Field(default="postgres", alias="DB_PASSWORD")
    test_database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/core_crewsim_test",
        alias="TEST_DATABASE_URL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        """Build the SQLAlchemy URL from deployment-friendly DB_* variables."""
        if self.database_url:
            return self

        username = quote(self.db_username, safe="")
        password = quote(self.db_password, safe="")
        database = quote(self.db_database, safe="")
        host = self.db_host
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"

        self.database_url = (
            f"postgresql+psycopg://{username}:{password}@{host}:{self.db_port}/{database}"
        )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

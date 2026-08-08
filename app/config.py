from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "core-crewsim"
    app_env: str = "development"
    app_debug: bool = True
    api_prefix: str = "/api"
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/core_crewsim",
        alias="DATABASE_URL",
    )
    test_database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/core_crewsim_test",
        alias="TEST_DATABASE_URL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

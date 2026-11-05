from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "community-llm-api"
    version: str = "0.1.0"
    environment: str = "local"
    cors_origins: list[str] = ["http://localhost:3000"]
    database_url: str = Field(
        default="postgresql+asyncpg://community:community@localhost:5433/community_llm",
        validation_alias=AliasChoices("DATABASE_URL", "COMMUNITY_LLM_DATABASE_URL"),
    )

    model_config = SettingsConfigDict(
        env_prefix="COMMUNITY_LLM_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

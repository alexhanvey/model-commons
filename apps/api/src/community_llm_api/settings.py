from __future__ import annotations

from functools import lru_cache
from typing import Self

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SESSION_SECRET = "dev-only-change-me"


class Settings(BaseSettings):
    app_name: str = "community-llm-api"
    version: str = "0.1.0"
    environment: str = "local"
    cors_origins: list[str] = ["http://localhost:3000"]
    database_url: str = Field(
        default="postgresql+asyncpg://community:community@localhost:5433/community_llm",
        validation_alias=AliasChoices("DATABASE_URL", "COMMUNITY_LLM_DATABASE_URL"),
    )
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:3000/api/v1/auth/github/callback"
    web_base_url: str = "http://localhost:3000"
    session_secret: str = DEV_SESSION_SECRET
    session_cookie_name: str = "community_session"
    oauth_state_cookie_name: str = "community_oauth_state"
    session_ttl_seconds: int = 60 * 60 * 24 * 7
    admin_github_ids: list[int] = Field(default_factory=list)
    artifact_dir: str = ".sandbox/artifacts"
    job_lease_seconds: int = 300
    max_job_attempts: int = 3
    max_artifact_bytes: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_prefix="COMMUNITY_LLM_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    @model_validator(mode="after")
    def _validate_session_secret(self) -> Self:
        if self.environment not in {"local", "test"} and (
            self.session_secret == DEV_SESSION_SECRET or len(self.session_secret) < 32
        ):
            raise ValueError(
                "COMMUNITY_LLM_SESSION_SECRET must be at least 32 characters outside local and test"
            )
        return self

    @property
    def cookie_secure(self) -> bool:
        return self.environment not in {"local", "test"}

    @property
    def github_oauth_configured(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()

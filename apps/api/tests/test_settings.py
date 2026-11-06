from __future__ import annotations

import pytest
from community_llm_api.settings import Settings
from pydantic import ValidationError


def _settings() -> Settings:
    # pydantic-settings accepts _env_file at runtime; mypy does not model it.
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_database_url_uses_database_url_env(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db:5432/app")
    monkeypatch.delenv("COMMUNITY_LLM_DATABASE_URL", raising=False)

    settings = _settings()

    assert settings.database_url == "postgresql+asyncpg://user:pass@db:5432/app"


def test_database_url_accepts_prefixed_env(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "COMMUNITY_LLM_DATABASE_URL",
        "postgresql+asyncpg://user:pass@db:5432/prefixed",
    )

    settings = _settings()

    assert settings.database_url == "postgresql+asyncpg://user:pass@db:5432/prefixed"


def test_database_url_default(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("COMMUNITY_LLM_DATABASE_URL", raising=False)

    settings = _settings()

    assert settings.database_url == (
        "postgresql+asyncpg://community:community@localhost:5433/community_llm"
    )


def test_local_cookie_and_oauth_defaults(monkeypatch) -> None:
    monkeypatch.setenv("COMMUNITY_LLM_ENVIRONMENT", "local")
    monkeypatch.delenv("COMMUNITY_LLM_GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("COMMUNITY_LLM_GITHUB_CLIENT_SECRET", raising=False)

    settings = _settings()

    assert settings.cookie_secure is False
    assert settings.github_oauth_configured is False
    assert (
        settings.github_redirect_uri
        == "http://localhost:3000/api/v1/auth/github/callback"
    )


def test_production_requires_session_secret(monkeypatch) -> None:
    monkeypatch.setenv("COMMUNITY_LLM_ENVIRONMENT", "production")
    monkeypatch.delenv("COMMUNITY_LLM_SESSION_SECRET", raising=False)

    with pytest.raises(ValidationError):
        _settings()


def test_production_accepts_session_secret(monkeypatch) -> None:
    monkeypatch.setenv("COMMUNITY_LLM_ENVIRONMENT", "production")
    monkeypatch.setenv("COMMUNITY_LLM_SESSION_SECRET", "0123456789abcdef0123456789abcdef")

    settings = _settings()

    assert settings.cookie_secure is True

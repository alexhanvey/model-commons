from __future__ import annotations

from community_llm_api.settings import Settings


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

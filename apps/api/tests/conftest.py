from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from community_llm_api.db import get_session
from community_llm_api.dependencies import get_github_client
from community_llm_api.github import GitHubOAuthError, GitHubUser
from community_llm_api.main import app
from community_llm_api.models import Base
from community_llm_api.settings import Settings, get_settings
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


class FakeGitHubClient:
    async def exchange_code(self, code: str) -> str:
        if code != "good-code":
            raise GitHubOAuthError("bad code")
        return "access-token"

    async def fetch_user(self, access_token: str) -> GitHubUser:
        return GitHubUser(
            id=12345,
            login="alexhanvey",
            name="Alex",
            email=None,
            avatar_url="https://example.com/avatar.png",
        )

    async def fetch_primary_email(self, access_token: str) -> str | None:
        return "alex@example.com"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(prepare())

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    test_settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        environment="test",
        github_client_id="test-client",
        github_client_secret="test-secret",
        session_secret="test-session-secret",
        admin_github_ids=[12345],
    )
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_github_client] = FakeGitHubClient

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


@pytest.fixture
def signed_in_client(client: TestClient) -> TestClient:
    login = client.get("/v1/auth/github/login", follow_redirects=False)
    state = login.cookies.get("community_oauth_state")
    assert state
    callback = client.get(
        "/v1/auth/github/callback",
        params={"code": "good-code", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    return client


@pytest.fixture
def csrf_token(signed_in_client: TestClient) -> str:
    response = signed_in_client.get("/v1/me")
    assert response.status_code == 200
    token = response.json()["csrf_token"]
    assert token
    return token

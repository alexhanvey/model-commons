from __future__ import annotations

import httpx
import pytest
from community_llm_api.github import GitHubOAuthClient, GitHubOAuthError


@pytest.mark.asyncio
async def test_exchange_code_fetches_user_and_email() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login/oauth/access_token":
            return httpx.Response(200, json={"access_token": "token"})
        if request.url.path == "/user":
            return httpx.Response(
                200,
                json={
                    "id": 1,
                    "login": "octocat",
                    "name": "Octo",
                    "avatar_url": "https://example.com/octo.png",
                },
            )
        if request.url.path == "/user/emails":
            return httpx.Response(
                200,
                json=[
                    {"email": "octo@example.com", "primary": True, "verified": True},
                    {"email": "other@example.com", "primary": False, "verified": True},
                ],
            )
        return httpx.Response(404)

    client = GitHubOAuthClient(
        "client-id",
        "client-secret",
        "http://localhost:8000/v1/auth/github/callback",
        transport=httpx.MockTransport(handler),
    )

    token = await client.exchange_code("code")
    user = await client.fetch_user(token)
    email = await client.fetch_primary_email(token)

    assert token == "token"
    assert user.login == "octocat"
    assert email == "octo@example.com"


@pytest.mark.asyncio
async def test_exchange_code_raises_without_access_token() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"error": "bad_verification_code"})
    )
    client = GitHubOAuthClient(
        "client-id",
        "client-secret",
        "http://localhost:8000/v1/auth/github/callback",
        transport=transport,
    )

    with pytest.raises(GitHubOAuthError):
        await client.exchange_code("bad-code")

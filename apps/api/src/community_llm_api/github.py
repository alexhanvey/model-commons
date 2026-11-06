from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"


class GitHubOAuthError(RuntimeError):
    """Raised when GitHub rejects an OAuth exchange or API call."""


class GitHubUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None


class GitHubOAuthClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._transport = transport

    @asynccontextmanager
    async def _client(self) -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(
            timeout=10.0,
            transport=self._transport,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        ) as client:
            yield client

    async def exchange_code(self, code: str) -> str:
        async with self._client() as client:
            try:
                response = await client.post(
                    GITHUB_TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise GitHubOAuthError("GitHub token exchange failed") from exc

        payload: dict[str, Any] = response.json()
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            detail = payload.get("error_description") or payload.get("error")
            raise GitHubOAuthError(str(detail or "GitHub returned no access token"))
        return access_token

    async def fetch_user(self, access_token: str) -> GitHubUser:
        async with self._client() as client:
            try:
                response = await client.get(
                    f"{GITHUB_API_URL}/user",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise GitHubOAuthError("GitHub user fetch failed") from exc

        return GitHubUser.model_validate(response.json())

    async def fetch_primary_email(self, access_token: str) -> str | None:
        async with self._client() as client:
            try:
                response = await client.get(
                    f"{GITHUB_API_URL}/user/emails",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
            except httpx.HTTPError:
                return None

        payload = response.json()
        if not isinstance(payload, list):
            return None
        verified = [
            item for item in payload if isinstance(item, dict) and item.get("verified") is True
        ]
        primary = next((item for item in verified if item.get("primary") is True), None)
        chosen = primary or (verified[0] if verified else None)
        if chosen is None:
            return None
        email = chosen.get("email")
        return email if isinstance(email, str) else None

from __future__ import annotations

import hashlib
import hmac
import secrets
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from community_llm_api.db import get_session
from community_llm_api.github import GitHubOAuthClient
from community_llm_api.models.user import User
from community_llm_api.models.user_session import UserSession
from community_llm_api.settings import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def derive_csrf_token(secret: str, session_token: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        f"csrf:{session_token}".encode(),
        hashlib.sha256,
    ).digest()
    return urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class SessionContext:
    user_session: UserSession
    user: User
    csrf_token: str


def get_github_client(settings: SettingsDep) -> GitHubOAuthClient:
    return GitHubOAuthClient(
        settings.github_client_id,
        settings.github_client_secret,
        settings.github_redirect_uri,
    )


GitHubClientDep = Annotated[GitHubOAuthClient, Depends(get_github_client)]


async def get_session_context(
    request: Request,
    db: SessionDep,
    settings: SettingsDep,
) -> SessionContext:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise _unauthorized("not authenticated")

    result = await db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.token_hash == hash_token(token))
    )
    row = result.one_or_none()
    if row is None:
        raise _unauthorized("not authenticated")

    user_session, user = row
    if user_session.revoked_at is not None:
        raise _unauthorized("session revoked")

    expires_at = user_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise _unauthorized("session expired")

    return SessionContext(
        user_session=user_session,
        user=user,
        csrf_token=derive_csrf_token(settings.session_secret, token),
    )


SessionContextDep = Annotated[SessionContext, Depends(get_session_context)]


async def get_current_user(context: SessionContextDep) -> User:
    return context.user


async def require_csrf(request: Request, context: SessionContextDep) -> SessionContext:
    token = request.headers.get("X-CSRF-Token")
    if not token or not secrets.compare_digest(token, context.csrf_token):
        raise HTTPException(status_code=403, detail="invalid CSRF token")
    return context


CsrfContextDep = Annotated[SessionContext, Depends(require_csrf)]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

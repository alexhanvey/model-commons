from __future__ import annotations

import hashlib
import hmac
import secrets
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from community_llm_protocol import Scope
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from community_llm_api.db import get_session
from community_llm_api.github import GitHubOAuthClient
from community_llm_api.models.api_key import ApiKey
from community_llm_api.models.user import User
from community_llm_api.models.user_session import UserSession
from community_llm_api.models.worker import Worker
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


@dataclass(frozen=True)
class Principal:
    user: User
    auth_method: Literal["session", "api_key"]
    scopes: frozenset[str]
    csrf_token: str | None = None
    api_key: ApiKey | None = None


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def get_github_client(settings: SettingsDep) -> GitHubOAuthClient:
    return GitHubOAuthClient(
        settings.github_client_id,
        settings.github_client_secret,
        settings.github_redirect_uri,
    )


GitHubClientDep = Annotated[GitHubOAuthClient, Depends(get_github_client)]


async def _session_context_from_request(
    request: Request,
    db: AsyncSession,
    settings: Settings,
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


async def get_session_context(
    request: Request,
    db: SessionDep,
    settings: SettingsDep,
) -> SessionContext:
    return await _session_context_from_request(request, db, settings)


SessionContextDep = Annotated[SessionContext, Depends(get_session_context)]


async def get_current_user(context: SessionContextDep) -> User:
    return context.user


async def require_csrf(request: Request, context: SessionContextDep) -> SessionContext:
    token = request.headers.get("X-CSRF-Token")
    if not token or not secrets.compare_digest(token, context.csrf_token):
        raise HTTPException(status_code=403, detail="invalid CSRF token")
    return context


CsrfContextDep = Annotated[SessionContext, Depends(require_csrf)]


async def require_admin_csrf(context: CsrfContextDep) -> SessionContext:
    if not context.user.is_admin:
        raise HTTPException(status_code=403, detail="admin access required")
    return context


AdminCsrfContextDep = Annotated[SessionContext, Depends(require_admin_csrf)]


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _ensure_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


async def get_principal(
    request: Request,
    db: SessionDep,
    settings: SettingsDep,
) -> Principal:
    token = _bearer_token(request)
    if token:
        if token.startswith("wrk_"):
            raise HTTPException(
                status_code=403, detail="worker tokens cannot access user endpoints"
            )
        if not token.startswith("clm_"):
            raise _unauthorized("invalid API key")

        result = await db.execute(
            select(ApiKey, User)
            .join(User, User.id == ApiKey.user_id)
            .where(ApiKey.token_hash == hash_token(token))
        )
        row = result.one_or_none()
        if row is None:
            raise _unauthorized("invalid API key")

        api_key, user = row
        if api_key.revoked_at is not None:
            raise _unauthorized("API key revoked")
        if api_key.expires_at is not None and _ensure_aware(api_key.expires_at) <= datetime.now(
            UTC
        ):
            raise _unauthorized("API key expired")

        now = datetime.now(UTC)
        if api_key.last_used_at is None or (now - _ensure_aware(api_key.last_used_at)) > timedelta(
            minutes=5
        ):
            api_key.last_used_at = now
            await db.commit()

        return Principal(
            user=user,
            auth_method="api_key",
            scopes=frozenset(api_key.scopes),
            api_key=api_key,
        )

    context = await _session_context_from_request(request, db, settings)
    return Principal(
        user=context.user,
        auth_method="session",
        scopes=frozenset(scope.value for scope in Scope),
        csrf_token=context.csrf_token,
    )


PrincipalDep = Annotated[Principal, Depends(get_principal)]


def require_scope(scope: Scope):
    async def dependency(principal: PrincipalDep) -> Principal:
        if principal.auth_method == "session":
            return principal
        if scope.value not in principal.scopes:
            raise HTTPException(status_code=403, detail=f"missing scope: {scope.value}")
        return principal

    return dependency


async def get_worker(request: Request, db: SessionDep) -> Worker:
    token = _bearer_token(request)
    if not token or not token.startswith("wrk_"):
        raise _unauthorized("invalid worker token")

    result = await db.execute(select(Worker).where(Worker.token_hash == hash_token(token)))
    worker = result.scalar_one_or_none()
    if worker is None:
        raise _unauthorized("invalid worker token")
    if worker.status == "revoked":
        raise _unauthorized("worker revoked")
    if worker.status != "approved":
        raise HTTPException(status_code=403, detail="worker not approved")
    return worker


WorkerDep = Annotated[Worker, Depends(get_worker)]

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from community_llm_api.dependencies import (
    CsrfContextDep,
    GitHubClientDep,
    SessionDep,
    SettingsDep,
    hash_token,
)
from community_llm_api.github import GITHUB_AUTHORIZE_URL, GitHubOAuthError
from community_llm_api.models.user import User
from community_llm_api.models.user_session import UserSession

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.get("/github/login")
async def github_login(settings: SettingsDep) -> RedirectResponse:
    if not settings.github_oauth_configured:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
    )
    response = RedirectResponse(f"{GITHUB_AUTHORIZE_URL}?{query}", status_code=302)
    response.set_cookie(
        settings.oauth_state_cookie_name,
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        # Must be readable at both /v1/auth/... (direct API) and
        # /api/v1/auth/... (Next.js proxy).
        path="/",
    )
    return response


@router.get("/github/callback")
async def github_callback(
    request: Request,
    db: SessionDep,
    settings: SettingsDep,
    github: GitHubClientDep,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    if not settings.github_oauth_configured:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    cookie_state = request.cookies.get(settings.oauth_state_cookie_name)
    if not code or not state or not cookie_state or not secrets.compare_digest(state, cookie_state):
        raise HTTPException(status_code=400, detail="invalid OAuth state")

    try:
        access_token = await github.exchange_code(code)
        github_user = await github.fetch_user(access_token)
        email = await github.fetch_primary_email(access_token) or github_user.email
    except GitHubOAuthError as exc:
        raise HTTPException(status_code=502, detail="GitHub OAuth failed") from exc

    result = await db.execute(select(User).where(User.github_id == github_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(github_id=github_user.id, login=github_user.login)
        db.add(user)

    user.login = github_user.login
    user.name = github_user.name
    user.email = email
    user.avatar_url = github_user.avatar_url
    user.is_admin = github_user.id in settings.admin_github_ids
    await db.flush()

    raw_token = secrets.token_urlsafe(48)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.session_ttl_seconds),
            user_agent=(request.headers.get("user-agent") or "")[:500] or None,
            ip_address=request.client.host if request.client else None,
        )
    )
    await db.commit()

    response = RedirectResponse(
        f"{settings.web_base_url.rstrip('/')}/",
        status_code=302,
    )
    response.delete_cookie(settings.oauth_state_cookie_name, path="/")
    response.set_cookie(
        settings.session_cookie_name,
        raw_token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    context: CsrfContextDep,
    db: SessionDep,
    settings: SettingsDep,
) -> Response:
    context.user_session.revoked_at = datetime.now(UTC)
    await db.commit()

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return response

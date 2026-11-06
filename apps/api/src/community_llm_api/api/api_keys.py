from __future__ import annotations

import secrets
from datetime import UTC, datetime
from uuid import UUID

from community_llm_protocol import ApiKeyCreate, ApiKeyCreated, ApiKeyPublic
from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from community_llm_api.dependencies import (
    CsrfContextDep,
    SessionContextDep,
    SessionDep,
    hash_token,
)
from community_llm_api.models.api_key import ApiKey

router = APIRouter(prefix="/v1/api-keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate,
    context: CsrfContextDep,
    db: SessionDep,
) -> ApiKeyCreated:
    token = f"clm_{secrets.token_urlsafe(32)}"
    api_key = ApiKey(
        user_id=context.user.id,
        name=payload.name,
        prefix=token[:12],
        token_hash=hash_token(token),
        scopes=sorted({scope.value for scope in payload.scopes}),
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return ApiKeyCreated(api_key=ApiKeyPublic.model_validate(api_key), token=token)


@router.get("", response_model=list[ApiKeyPublic])
async def list_api_keys(
    context: SessionContextDep,
    db: SessionDep,
) -> list[ApiKeyPublic]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == context.user.id).order_by(ApiKey.created_at.desc())
    )
    return [ApiKeyPublic.model_validate(api_key) for api_key in result.scalars()]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    context: CsrfContextDep,
    db: SessionDep,
) -> Response:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == context.user.id)
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")

    if api_key.revoked_at is None:
        api_key.revoked_at = datetime.now(UTC)
        await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

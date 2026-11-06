from __future__ import annotations

from community_llm_protocol import MeResponse, UserPublic
from fastapi import APIRouter

from community_llm_api.dependencies import SessionContextDep

router = APIRouter(tags=["auth"])


@router.get("/v1/me", response_model=MeResponse)
async def me(context: SessionContextDep) -> MeResponse:
    return MeResponse(
        user=UserPublic.model_validate(context.user),
        csrf_token=context.csrf_token,
    )

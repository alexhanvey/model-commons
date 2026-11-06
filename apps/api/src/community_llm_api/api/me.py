from __future__ import annotations

from community_llm_protocol import MeResponse, UserPublic
from fastapi import APIRouter

from community_llm_api.dependencies import PrincipalDep

router = APIRouter(tags=["auth"])


@router.get("/v1/me", response_model=MeResponse)
async def me(principal: PrincipalDep) -> MeResponse:
    return MeResponse(
        user=UserPublic.model_validate(principal.user),
        csrf_token=principal.csrf_token,
        auth_method=principal.auth_method,
    )

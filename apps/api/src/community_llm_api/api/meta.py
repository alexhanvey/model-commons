from __future__ import annotations

from community_llm_protocol import MetaResponse
from fastapi import APIRouter

from community_llm_api.settings import get_settings

router = APIRouter(tags=["system"])


@router.get("/v1/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    settings = get_settings()
    return MetaResponse(
        name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
    )

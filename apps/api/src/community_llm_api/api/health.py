from __future__ import annotations

from community_llm_protocol import HealthResponse
from fastapi import APIRouter

from community_llm_api.settings import get_settings

router = APIRouter(tags=["system"])


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(service=get_settings().app_name)


@router.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    # Dependency checks are added in Phase 2 once Postgres, Redis, and S3 are wired.
    return HealthResponse(status="ok", service=get_settings().app_name)

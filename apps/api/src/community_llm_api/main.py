from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from community_llm_api.api.admin import router as admin_router
from community_llm_api.api.api_keys import router as api_keys_router
from community_llm_api.api.auth import router as auth_router
from community_llm_api.api.health import router as health_router
from community_llm_api.api.jobs import router as jobs_router
from community_llm_api.api.me import router as me_router
from community_llm_api.api.meta import router as meta_router
from community_llm_api.api.model_versions import admin_router as model_versions_admin_router
from community_llm_api.api.model_versions import router as model_versions_router
from community_llm_api.api.points import router as points_router
from community_llm_api.api.worker_jobs import router as worker_jobs_router
from community_llm_api.api.workers import router as workers_router
from community_llm_api.db import dispose_engine
from community_llm_api.logging import configure_logging
from community_llm_api.settings import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(
        title="Community LLM API",
        version=settings.version,
        description="Control-plane API for the community-owned small-model network.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(meta_router)
    app.include_router(auth_router)
    app.include_router(me_router)
    app.include_router(api_keys_router)
    app.include_router(workers_router)
    app.include_router(jobs_router)
    app.include_router(points_router)
    app.include_router(admin_router)
    app.include_router(worker_jobs_router)
    app.include_router(model_versions_router)
    app.include_router(model_versions_admin_router)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"service": settings.app_name, "docs": "/docs"}

    return app


app = create_app()

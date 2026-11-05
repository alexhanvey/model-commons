from __future__ import annotations

from community_llm_protocol import HealthResponse
from fastapi import FastAPI

app = FastAPI(
    title="Community LLM Inference",
    version="0.1.0",
    description="OpenAI-compatible inference proxy for a trusted vLLM host.",
)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(service="community-llm-inference")


@app.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    # Upstream vLLM readiness is added in Phase 5.
    return HealthResponse(status="ok", service="community-llm-inference")


@app.get("/v1/models")
def models() -> dict[str, list[object]]:
    return {"data": []}

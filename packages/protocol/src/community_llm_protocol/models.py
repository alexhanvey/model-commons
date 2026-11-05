from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    service: str


class MetaResponse(BaseModel):
    name: str
    version: str
    environment: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: str | None = None

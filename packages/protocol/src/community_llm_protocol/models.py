from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    is_admin: bool = False


class Scope(StrEnum):
    INFERENCE_WRITE = "inference:write"
    JOBS_READ = "jobs:read"
    JOBS_WRITE = "jobs:write"


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[Scope] = Field(min_length=1)


class ApiKeyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    prefix: str
    scopes: list[Scope]
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime | None = None


class ApiKeyCreated(BaseModel):
    api_key: ApiKeyPublic
    token: str


WorkerStatus = Literal["pending", "approved", "revoked"]


class WorkerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class WorkerPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: WorkerStatus
    created_at: datetime
    approved_at: datetime | None = None
    last_heartbeat_at: datetime | None = None


class WorkerCreated(BaseModel):
    worker: WorkerPublic
    token: str


class MeResponse(BaseModel):
    user: UserPublic
    csrf_token: str | None = None
    auth_method: Literal["session", "api_key"] = "session"

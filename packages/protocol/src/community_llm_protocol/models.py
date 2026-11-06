from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
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


class JobKind(StrEnum):
    BENCHMARK = "benchmark"
    EVAL = "eval"
    LORA_FINETUNE = "lora_finetune"


class JobStatus(StrEnum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    UPLOADED = "uploaded"
    VERIFIED = "verified"
    PAID = "paid"
    FAILED = "failed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class JobCreate(BaseModel):
    kind: JobKind
    spec: dict[str, Any] = Field(default_factory=dict)


class JobPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    kind: JobKind
    status: JobStatus
    spec: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None = None


class JobAttemptStatus(StrEnum):
    ASSIGNED = "assigned"
    RUNNING = "running"
    UPLOADED = "uploaded"
    FAILED = "failed"
    EXPIRED = "expired"


class JobAttemptPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    attempt_number: int
    worker_id: UUID | None = None
    status: JobAttemptStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    lease_expires_at: datetime | None = None
    error: str | None = None
    created_at: datetime


class JobAssignment(BaseModel):
    job: JobPublic
    attempt: JobAttemptPublic
    lease_expires_at: datetime | None = None


class WorkerJobComplete(BaseModel):
    logs: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class WorkerJobFail(BaseModel):
    error: str = Field(min_length=1, max_length=1000)
    logs: str | None = None


class JobArtifactPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    name: str
    uri: str
    sha256: str
    size_bytes: int
    content_type: str | None = None
    created_at: datetime


class JobResultPublic(BaseModel):
    logs: str | None = None
    metrics: dict[str, Any] | None = None
    error: str | None = None


class LedgerTransactionType(StrEnum):
    GRANT = "grant"
    SPEND = "spend"
    HOLD = "hold"
    SETTLE = "settle"
    RELEASE = "release"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class LedgerEntryPublic(BaseModel):
    account: str
    direction: Literal["debit", "credit"]
    amount: int


class LedgerTransactionPublic(BaseModel):
    id: UUID
    type: LedgerTransactionType
    description: str | None = None
    created_at: datetime
    entries: list[LedgerEntryPublic]


class PointsBalance(BaseModel):
    available: int
    held: int


class AdminGrantCreate(BaseModel):
    user_id: UUID
    amount: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=1, max_length=100)


class AdminGrantResponse(BaseModel):
    transaction_id: UUID
    available: int


class LedgerReconciliation(BaseModel):
    ok: bool
    transactions: int
    unbalanced_transactions: int
    negative_accounts: int
    total_debits: int
    total_credits: int

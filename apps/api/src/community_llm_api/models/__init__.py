from __future__ import annotations

from community_llm_api.models.api_key import ApiKey
from community_llm_api.models.artifact import Artifact
from community_llm_api.models.audit import AuditEvent
from community_llm_api.models.base import Base
from community_llm_api.models.gpu_device import GpuDevice
from community_llm_api.models.idempotency_key import IdempotencyKey
from community_llm_api.models.job import Job, JobAttempt
from community_llm_api.models.ledger import LedgerAccount, LedgerEntry, LedgerTransaction
from community_llm_api.models.user import User
from community_llm_api.models.user_session import UserSession
from community_llm_api.models.worker import Worker

# Alembic imports this module to populate Base.metadata. Add new models here.
__all__ = [
    "ApiKey",
    "Artifact",
    "AuditEvent",
    "Base",
    "GpuDevice",
    "IdempotencyKey",
    "Job",
    "JobAttempt",
    "LedgerAccount",
    "LedgerEntry",
    "LedgerTransaction",
    "User",
    "UserSession",
    "Worker",
]

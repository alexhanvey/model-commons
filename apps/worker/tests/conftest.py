from __future__ import annotations

from typing import Any

import pytest

CREATED_AT = "2026-11-06T00:00:00Z"
JOB_ID = "00000000-0000-0000-0000-000000000001"
USER_ID = "00000000-0000-0000-0000-000000000002"
ATTEMPT_ID = "00000000-0000-0000-0000-000000000003"
WORKER_ID = "00000000-0000-0000-0000-000000000004"
ARTIFACT_ID = "00000000-0000-0000-0000-000000000005"


@pytest.fixture
def job_payload() -> dict[str, Any]:
    return {
        "id": JOB_ID,
        "user_id": USER_ID,
        "kind": "eval",
        "status": "assigned",
        "spec": {"suite": "smoke"},
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
        "cancelled_at": None,
    }


@pytest.fixture
def attempt_payload(job_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": ATTEMPT_ID,
        "job_id": job_payload["id"],
        "attempt_number": 1,
        "worker_id": WORKER_ID,
        "status": "assigned",
        "started_at": None,
        "finished_at": None,
        "lease_expires_at": CREATED_AT,
        "error": None,
        "created_at": CREATED_AT,
    }


@pytest.fixture
def assignment_payload(
    job_payload: dict[str, Any],
    attempt_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "job": job_payload,
        "attempt": attempt_payload,
        "lease_expires_at": CREATED_AT,
    }


@pytest.fixture
def worker_payload() -> dict[str, Any]:
    return {
        "id": WORKER_ID,
        "name": "gpu-1",
        "status": "approved",
        "created_at": CREATED_AT,
        "approved_at": CREATED_AT,
        "last_heartbeat_at": CREATED_AT,
    }


@pytest.fixture
def artifact_payload(job_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": ARTIFACT_ID,
        "job_id": job_payload["id"],
        "name": "result.json",
        "uri": "file:///tmp/result.json",
        "sha256": "a" * 64,
        "size_bytes": 2,
        "content_type": "application/json",
        "created_at": CREATED_AT,
    }

from __future__ import annotations

from uuid import UUID

import pytest
from community_llm_api.job_state import (
    InvalidJobTransition,
    assert_transition,
    can_transition,
)
from community_llm_protocol import JobStatus
from fastapi.testclient import TestClient

ALLOWED = [
    (JobStatus.QUEUED, JobStatus.ASSIGNED),
    (JobStatus.QUEUED, JobStatus.CANCELLED),
    (JobStatus.QUEUED, JobStatus.EXPIRED),
    (JobStatus.ASSIGNED, JobStatus.RUNNING),
    (JobStatus.ASSIGNED, JobStatus.FAILED),
    (JobStatus.ASSIGNED, JobStatus.CANCELLED),
    (JobStatus.RUNNING, JobStatus.UPLOADED),
    (JobStatus.RUNNING, JobStatus.FAILED),
    (JobStatus.RUNNING, JobStatus.CANCELLED),
    (JobStatus.UPLOADED, JobStatus.VERIFIED),
    (JobStatus.UPLOADED, JobStatus.REJECTED),
    (JobStatus.VERIFIED, JobStatus.PAID),
    (JobStatus.FAILED, JobStatus.QUEUED),
]

INVALID = [
    (JobStatus.QUEUED, JobStatus.RUNNING),
    (JobStatus.QUEUED, JobStatus.PAID),
    (JobStatus.UPLOADED, JobStatus.CANCELLED),
    (JobStatus.VERIFIED, JobStatus.CANCELLED),
    (JobStatus.PAID, JobStatus.QUEUED),
    (JobStatus.CANCELLED, JobStatus.QUEUED),
    (JobStatus.FAILED, JobStatus.RUNNING),
]


@pytest.mark.parametrize(("current", "requested"), ALLOWED)
def test_allowed_transitions(current: JobStatus, requested: JobStatus) -> None:
    assert can_transition(current, requested)
    assert_transition(current, requested)


@pytest.mark.parametrize(("current", "requested"), INVALID)
def test_invalid_transitions(current: JobStatus, requested: JobStatus) -> None:
    assert not can_transition(current, requested)
    with pytest.raises(InvalidJobTransition):
        assert_transition(current, requested)


def test_job_create_list_get_and_cancel(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    created = signed_in_client.post(
        "/v1/jobs",
        json={"kind": "eval", "spec": {"suite": "smoke"}},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert created.status_code == 201

    job = created.json()
    assert job["kind"] == "eval"
    assert job["status"] == "queued"
    assert job["spec"] == {"suite": "smoke"}

    listed = signed_in_client.get("/v1/jobs")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [job["id"]]

    fetched = signed_in_client.get(f"/v1/jobs/{job['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == job["id"]

    cancelled = signed_in_client.post(
        f"/v1/jobs/{job['id']}/cancel",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_at"] is not None

    again = signed_in_client.post(
        f"/v1/jobs/{job['id']}/cancel",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert again.status_code == 409


def test_job_create_requires_csrf(signed_in_client: TestClient) -> None:
    response = signed_in_client.post("/v1/jobs", json={"kind": "benchmark"})
    assert response.status_code == 403


def test_job_create_rejects_unknown_kind(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    response = signed_in_client.post(
        "/v1/jobs",
        json={"kind": "not-a-kind"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 422


def test_job_stores_recipe_ref(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    recipe_ref = {
        "repository": "model-commons/recipes",
        "commit": "a" * 40,
        "path": "recipes/granite-4.1-3b/issue-tracker/v3",
        "manifest_sha256": "b" * 64,
    }
    response = signed_in_client.post(
        "/v1/jobs",
        json={"kind": "lora_finetune", "spec": {}, "recipe_ref": recipe_ref},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 201
    assert response.json()["recipe_ref"] == recipe_ref


def test_unknown_job_is_404(signed_in_client: TestClient) -> None:
    job_id = UUID("00000000-0000-0000-0000-000000000000")
    assert signed_in_client.get(f"/v1/jobs/{job_id}").status_code == 404

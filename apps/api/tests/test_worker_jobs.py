from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from community_llm_api.models.job import JobAttempt
from fastapi.testclient import TestClient


def _create_worker(
    client: TestClient,
    csrf_token: str,
    name: str = "gpu-1",
) -> tuple[dict, str]:
    response = client.post(
        "/v1/workers",
        json={"name": name},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 201
    body = response.json()
    approved = client.post(
        f"/v1/workers/{body['worker']['id']}/approve",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert approved.status_code == 200
    return body["worker"], body["token"]


def _create_job(client: TestClient, csrf_token: str, kind: str = "eval") -> dict:
    response = client.post(
        "/v1/jobs",
        json={"kind": kind, "spec": {"suite": "smoke"}},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 201
    return response.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _next(client: TestClient, token: str) -> dict:
    response = client.post("/v1/worker/jobs/next", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()
    assert body is not None
    return body


def _start(client: TestClient, token: str, attempt_id: str) -> dict:
    response = client.post(
        f"/v1/worker/jobs/{attempt_id}/start",
        headers=_auth(token),
    )
    assert response.status_code == 200
    return response.json()


def _upload_result(client: TestClient, token: str, attempt_id: str) -> dict:
    data = b'{"ok": true}'
    digest = hashlib.sha256(data).hexdigest()
    response = client.post(
        f"/v1/worker/jobs/{attempt_id}/artifacts",
        headers=_auth(token),
        files={"file": ("result.json", data, "application/json")},
        data={"expected_sha256": digest},
    )
    assert response.status_code == 201
    artifact = response.json()
    assert artifact["sha256"] == digest
    assert artifact["size_bytes"] == len(data)
    return artifact


@pytest.mark.parametrize(
    ("kind", "reward"),
    [("benchmark", 10), ("eval", 20), ("lora_finetune", 50)],
)
def test_fake_gpu_end_to_end(
    signed_in_client: TestClient,
    csrf_token: str,
    kind: str,
    reward: int,
) -> None:
    _worker, worker_token = _create_worker(signed_in_client, csrf_token)
    job = _create_job(signed_in_client, csrf_token, kind)
    assignment = _next(signed_in_client, worker_token)
    attempt_id = assignment["attempt"]["id"]
    assert assignment["job"]["id"] == job["id"]

    started = _start(signed_in_client, worker_token, attempt_id)
    assert started["job"]["status"] == "running"

    heartbeat = signed_in_client.post(
        f"/v1/worker/jobs/{attempt_id}/heartbeat",
        headers=_auth(worker_token),
    )
    assert heartbeat.status_code == 200

    _upload_result(signed_in_client, worker_token, attempt_id)

    completed = signed_in_client.post(
        f"/v1/worker/jobs/{attempt_id}/complete",
        headers=_auth(worker_token),
        json={
            "logs": "used clm_secret and Bearer wrk_secret",
            "metrics": {"ok": True},
        },
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "uploaded"

    result = signed_in_client.get(f"/v1/jobs/{job['id']}/result")
    assert result.status_code == 200
    assert "clm_secret" not in result.json()["logs"]
    assert "wrk_secret" not in result.json()["logs"]
    assert result.json()["metrics"] == {"ok": True}

    worker_result = signed_in_client.get(
        f"/v1/worker/jobs/{attempt_id}/result",
        headers=_auth(worker_token),
    )
    assert worker_result.status_code == 200
    assert "clm_secret" not in worker_result.json()["logs"]

    artifacts = signed_in_client.get(f"/v1/jobs/{job['id']}/artifacts")
    assert artifacts.status_code == 200
    assert len(artifacts.json()) == 1

    verified = signed_in_client.post(
        f"/v1/admin/jobs/{job['id']}/verify",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "paid"

    balance = signed_in_client.get("/v1/points/balance")
    assert balance.json()["available"] == reward

    again = signed_in_client.post(
        f"/v1/admin/jobs/{job['id']}/verify",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert again.status_code == 409
    assert signed_in_client.get("/v1/points/balance").json()["available"] == reward


def test_worker_cannot_touch_another_workers_job(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    _worker_a, token_a = _create_worker(signed_in_client, csrf_token, "gpu-a")
    _worker_b, token_b = _create_worker(signed_in_client, csrf_token, "gpu-b")
    _job = _create_job(signed_in_client, csrf_token)
    assignment = _next(signed_in_client, token_a)
    attempt_id = assignment["attempt"]["id"]

    for path, payload in [
        (f"/v1/worker/jobs/{attempt_id}/start", None),
        (f"/v1/worker/jobs/{attempt_id}/heartbeat", None),
        (f"/v1/worker/jobs/{attempt_id}/complete", {"logs": "x", "metrics": {}}),
    ]:
        response = signed_in_client.post(
            path,
            headers=_auth(token_b),
            json=payload,
        )
        assert response.status_code == 404

    upload = signed_in_client.post(
        f"/v1/worker/jobs/{attempt_id}/artifacts",
        headers=_auth(token_b),
        files={"file": ("result.json", b"{}", "application/json")},
    )
    assert upload.status_code == 404


def test_failure_retries_then_fails(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    _worker, worker_token = _create_worker(signed_in_client, csrf_token)
    job = _create_job(signed_in_client, csrf_token)

    first = _next(signed_in_client, worker_token)
    _start(signed_in_client, worker_token, first["attempt"]["id"])
    failed_once = signed_in_client.post(
        f"/v1/worker/jobs/{first['attempt']['id']}/fail",
        headers=_auth(worker_token),
        json={"error": "boom 1", "logs": "clm_secret"},
    )
    assert failed_once.status_code == 200
    assert failed_once.json()["status"] == "queued"

    second = _next(signed_in_client, worker_token)
    assert second["attempt"]["attempt_number"] == 2
    _start(signed_in_client, worker_token, second["attempt"]["id"])
    failed_twice = signed_in_client.post(
        f"/v1/worker/jobs/{second['attempt']['id']}/fail",
        headers=_auth(worker_token),
        json={"error": "boom 2"},
    )
    assert failed_twice.status_code == 200
    assert failed_twice.json()["status"] == "failed"

    none_left = signed_in_client.post("/v1/worker/jobs/next", headers=_auth(worker_token))
    assert none_left.status_code == 200
    assert none_left.json() is None
    assert signed_in_client.get("/v1/points/balance").json()["available"] == 0

    fetched = signed_in_client.get(f"/v1/jobs/{job['id']}")
    assert fetched.json()["status"] == "failed"


def test_lease_expiry_requeues(
    signed_in_client: TestClient,
    csrf_token: str,
    session_factory,
) -> None:
    _worker, worker_token = _create_worker(signed_in_client, csrf_token)
    job = _create_job(signed_in_client, csrf_token)
    first = _next(signed_in_client, worker_token)
    first_attempt_id = first["attempt"]["id"]
    _start(signed_in_client, worker_token, first_attempt_id)

    async def expire() -> None:
        async with session_factory() as session:
            attempt = await session.get(JobAttempt, UUID(first_attempt_id))
            assert attempt is not None
            attempt.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await session.commit()

    asyncio.run(expire())

    second = _next(signed_in_client, worker_token)
    assert second["job"]["id"] == job["id"]
    assert second["attempt"]["id"] != first_attempt_id
    assert second["attempt"]["attempt_number"] == 2

    async def status() -> str:
        async with session_factory() as session:
            attempt = await session.get(JobAttempt, UUID(first_attempt_id))
            assert attempt is not None
            return attempt.status

    assert asyncio.run(status()) == "expired"


def test_pending_worker_cannot_poll(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    response = signed_in_client.post(
        "/v1/workers",
        json={"name": "pending"},
        headers={"X-CSRF-Token": csrf_token},
    )
    token = response.json()["token"]

    poll = signed_in_client.post("/v1/worker/jobs/next", headers=_auth(token))
    assert poll.status_code == 403


def test_verify_requires_an_artifact(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    _worker, worker_token = _create_worker(signed_in_client, csrf_token)
    job = _create_job(signed_in_client, csrf_token)
    assignment = _next(signed_in_client, worker_token)
    attempt_id = assignment["attempt"]["id"]
    _start(signed_in_client, worker_token, attempt_id)
    complete = signed_in_client.post(
        f"/v1/worker/jobs/{attempt_id}/complete",
        headers=_auth(worker_token),
        json={"logs": "done", "metrics": {}},
    )
    assert complete.status_code == 200

    verify = signed_in_client.post(
        f"/v1/admin/jobs/{job['id']}/verify",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert verify.status_code == 422
    assert signed_in_client.get("/v1/points/balance").json()["available"] == 0


def test_artifact_checksum_mismatch_is_rejected(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    _worker, worker_token = _create_worker(signed_in_client, csrf_token)
    _job = _create_job(signed_in_client, csrf_token)
    assignment = _next(signed_in_client, worker_token)
    attempt_id = assignment["attempt"]["id"]
    _start(signed_in_client, worker_token, attempt_id)

    response = signed_in_client.post(
        f"/v1/worker/jobs/{attempt_id}/artifacts",
        headers=_auth(worker_token),
        files={"file": ("result.json", b"{}", "application/json")},
        data={"expected_sha256": "0" * 64},
    )
    assert response.status_code == 422

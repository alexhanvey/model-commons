from __future__ import annotations

from fastapi.testclient import TestClient


def test_worker_lifecycle(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    created = signed_in_client.post(
        "/v1/workers",
        json={"name": "gpu-1"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert created.status_code == 201

    body = created.json()
    worker = body["worker"]
    token = body["token"]
    assert token.startswith("wrk_")
    assert worker["status"] == "pending"

    pending = signed_in_client.post(
        "/v1/workers/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pending.status_code == 403

    approved = signed_in_client.post(
        f"/v1/workers/{worker['id']}/approve",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["approved_at"] is not None

    heartbeat = signed_in_client.post(
        "/v1/workers/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["last_heartbeat_at"] is not None

    listed = signed_in_client.get("/v1/workers")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert "token" not in listed.json()[0]

    cannot_access_user = signed_in_client.get(
        "/v1/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cannot_access_user.status_code == 403

    revoked = signed_in_client.delete(
        f"/v1/workers/{worker['id']}",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert revoked.status_code == 204

    rejected = signed_in_client.post(
        "/v1/workers/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rejected.status_code == 401

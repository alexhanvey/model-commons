from __future__ import annotations

import json

import httpx
from community_llm_sdk import CommunityLLMClient

USER_ID = "00000000-0000-0000-0000-000000000001"
JOB_ID = "00000000-0000-0000-0000-000000000002"
WORKER_ID = "00000000-0000-0000-0000-000000000003"
CREATED_AT = "2026-11-06T00:00:00Z"


def test_health() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/healthz"
        return httpx.Response(200, json={"status": "ok", "service": "api"})

    with CommunityLLMClient(
        "http://test",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.health()

    assert result.status == "ok"
    assert result.service == "api"


def test_me_with_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/me"
        assert request.headers["authorization"] == "Bearer clm_test"
        return httpx.Response(
            200,
            json={
                "user": {
                    "id": USER_ID,
                    "login": "tester",
                    "name": None,
                    "email": None,
                    "avatar_url": None,
                    "is_admin": False,
                },
                "csrf_token": None,
                "auth_method": "api_key",
            },
        )

    with CommunityLLMClient(
        "http://test",
        api_key="clm_test",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.me()

    assert result.auth_method == "api_key"
    assert result.user.login == "tester"


def test_create_job_sends_session_and_csrf() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/jobs"
        assert request.headers["cookie"] == "community_session=session-value"
        assert request.headers["x-csrf-token"] == "csrf-value"
        assert json.loads(request.content) == {"kind": "eval", "spec": {"suite": "smoke"}}
        return httpx.Response(
            201,
            json={
                "id": JOB_ID,
                "user_id": USER_ID,
                "kind": "eval",
                "status": "queued",
                "spec": {"suite": "smoke"},
                "created_at": CREATED_AT,
                "updated_at": CREATED_AT,
                "cancelled_at": None,
            },
        )

    with CommunityLLMClient(
        "http://test",
        session_cookie="session-value",
        csrf_token="csrf-value",
        transport=httpx.MockTransport(handler),
    ) as client:
        job = client.create_job("eval", {"suite": "smoke"})

    assert job.status == "queued"
    assert job.kind == "eval"


def test_worker_heartbeat_uses_worker_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/workers/heartbeat"
        assert request.headers["authorization"] == "Bearer wrk_test"
        return httpx.Response(
            200,
            json={
                "id": WORKER_ID,
                "name": "gpu-1",
                "status": "approved",
                "created_at": CREATED_AT,
                "approved_at": CREATED_AT,
                "last_heartbeat_at": CREATED_AT,
            },
        )

    with CommunityLLMClient(
        "http://test",
        worker_token="wrk_test",
        transport=httpx.MockTransport(handler),
    ) as client:
        worker = client.worker_heartbeat()

    assert worker.status == "approved"


def test_admin_grant_sends_csrf_and_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/admin/grants"
        assert request.headers["x-csrf-token"] == "csrf-value"
        assert json.loads(request.content) == {
            "user_id": USER_ID,
            "amount": 25,
            "reason": "test",
            "idempotency_key": "grant-1",
        }
        return httpx.Response(
            200,
            json={
                "transaction_id": "00000000-0000-0000-0000-000000000004",
                "available": 25,
            },
        )

    with CommunityLLMClient(
        "http://test",
        session_cookie="session-value",
        csrf_token="csrf-value",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.admin_grant(USER_ID, 25, "test", "grant-1")

    assert result.available == 25

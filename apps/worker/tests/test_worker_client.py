from __future__ import annotations

import json
from typing import Any

import httpx
from community_llm_worker.client import WorkerClient, create_job, register_worker


def test_next_job(assignment_payload: dict[str, Any]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/worker/jobs/next"
        assert request.headers["authorization"] == "Bearer wrk_test"
        return httpx.Response(200, json=assignment_payload)

    with WorkerClient(
        "http://test",
        "wrk_test",
        transport=httpx.MockTransport(handler),
    ) as client:
        assignment = client.next_job()

    assert assignment is not None
    assert assignment.job.kind.value == "eval"


def test_next_job_none() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            content=b"null",
            headers={"content-type": "application/json"},
        )
    )
    with WorkerClient("http://test", "wrk_test", transport=transport) as client:
        assert client.next_job() is None


def test_start_job(
    assignment_payload: dict[str, Any],
) -> None:
    running = {
        **assignment_payload,
        "job": {**assignment_payload["job"], "status": "running"},
        "attempt": {**assignment_payload["attempt"], "status": "running"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/start")
        return httpx.Response(200, json=running)

    with WorkerClient(
        "http://test",
        "wrk_test",
        transport=httpx.MockTransport(handler),
    ) as client:
        assignment = client.start("attempt-id")

    assert assignment.job.status.value == "running"


def test_upload_artifact(artifact_payload: dict[str, Any]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/artifacts")
        assert request.headers["content-type"].startswith("multipart/form-data")
        assert b"result.json" in request.content
        return httpx.Response(201, json=artifact_payload)

    with WorkerClient(
        "http://test",
        "wrk_test",
        transport=httpx.MockTransport(handler),
    ) as client:
        artifact = client.upload_artifact("attempt-id", "result.json", b"{}")

    assert artifact.name == "result.json"


def test_register_worker(worker_payload: dict[str, Any]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/workers"
        assert request.headers["cookie"] == "community_session=session"
        assert request.headers["x-csrf-token"] == "csrf"
        assert json.loads(request.content) == {"name": "gpu-1"}
        return httpx.Response(201, json={"worker": worker_payload, "token": "wrk_test"})

    created = register_worker(
        "http://test",
        "gpu-1",
        "session",
        "csrf",
        transport=httpx.MockTransport(handler),
    )

    assert created.token == "wrk_test"
    assert created.worker.name == "gpu-1"


def test_create_job(job_payload: dict[str, Any]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/jobs"
        assert request.headers["x-csrf-token"] == "csrf"
        assert json.loads(request.content) == {"kind": "benchmark", "spec": {"suite": "smoke"}}
        return httpx.Response(201, json=job_payload)

    job = create_job(
        "http://test",
        "benchmark",
        {"suite": "smoke"},
        "session",
        "csrf",
        transport=httpx.MockTransport(handler),
    )

    assert str(job.id) == job_payload["id"]

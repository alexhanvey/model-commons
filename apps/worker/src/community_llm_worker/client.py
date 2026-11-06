from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from community_llm_protocol import (
    JobArtifactPublic,
    JobAssignment,
    JobKind,
    JobPublic,
    JobResultPublic,
    WorkerCreated,
    WorkerPublic,
)


class WorkerClient:
    def __init__(
        self,
        api_url: str,
        worker_token: str,
        *,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=api_url.rstrip("/"),
            timeout=timeout,
            headers={"Authorization": f"Bearer {worker_token}"},
            transport=transport,
        )

    def _post(self, path: str, **kwargs: Any) -> httpx.Response:
        response = self._client.post(path, **kwargs)
        response.raise_for_status()
        return response

    def heartbeat(self) -> WorkerPublic:
        return WorkerPublic.model_validate(self._post("/v1/workers/heartbeat").json())

    def next_job(self) -> JobAssignment | None:
        response = self._post("/v1/worker/jobs/next")
        if response.status_code == 204 or not response.content:
            return None
        payload = response.json()
        if payload is None:
            return None
        return JobAssignment.model_validate(payload)

    def start(self, attempt_id: UUID | str) -> JobAssignment:
        return JobAssignment.model_validate(
            self._post(f"/v1/worker/jobs/{attempt_id}/start").json()
        )

    def heartbeat_job(self, attempt_id: UUID | str) -> JobAssignment:
        return JobAssignment.model_validate(
            self._post(f"/v1/worker/jobs/{attempt_id}/heartbeat").json()
        )

    def upload_artifact(
        self,
        attempt_id: UUID | str,
        name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> JobArtifactPublic:
        response = self._post(
            f"/v1/worker/jobs/{attempt_id}/artifacts",
            files={"file": (name, data, content_type)},
        )
        return JobArtifactPublic.model_validate(response.json())

    def complete(
        self,
        attempt_id: UUID | str,
        logs: str | None,
        metrics: dict[str, object],
    ) -> JobPublic:
        response = self._post(
            f"/v1/worker/jobs/{attempt_id}/complete",
            json={"logs": logs, "metrics": metrics},
        )
        return JobPublic.model_validate(response.json())

    def fail(
        self,
        attempt_id: UUID | str,
        error: str,
        logs: str | None = None,
    ) -> JobPublic:
        response = self._post(
            f"/v1/worker/jobs/{attempt_id}/fail",
            json={"error": error, "logs": logs},
        )
        return JobPublic.model_validate(response.json())

    def result(self, attempt_id: UUID | str) -> JobResultPublic:
        response = self._client.get(f"/v1/worker/jobs/{attempt_id}/result")
        response.raise_for_status()
        return JobResultPublic.model_validate(response.json())

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> WorkerClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def _session_headers(session_cookie: str, csrf_token: str) -> dict[str, str]:
    return {
        "Cookie": f"community_session={session_cookie}",
        "X-CSRF-Token": csrf_token,
    }


def register_worker(
    api_url: str,
    name: str,
    session_cookie: str,
    csrf_token: str,
    *,
    timeout: float = 10.0,
    transport: httpx.BaseTransport | None = None,
) -> WorkerCreated:
    with httpx.Client(
        base_url=api_url.rstrip("/"),
        timeout=timeout,
        headers=_session_headers(session_cookie, csrf_token),
        transport=transport,
    ) as client:
        response = client.post("/v1/workers", json={"name": name})
        response.raise_for_status()
        return WorkerCreated.model_validate(response.json())


def create_job(
    api_url: str,
    kind: JobKind | str,
    spec: dict[str, object],
    session_cookie: str,
    csrf_token: str,
    *,
    timeout: float = 10.0,
    transport: httpx.BaseTransport | None = None,
) -> JobPublic:
    with httpx.Client(
        base_url=api_url.rstrip("/"),
        timeout=timeout,
        headers=_session_headers(session_cookie, csrf_token),
        transport=transport,
    ) as client:
        response = client.post(
            "/v1/jobs",
            json={"kind": kind.value if isinstance(kind, JobKind) else kind, "spec": spec},
        )
        response.raise_for_status()
        return JobPublic.model_validate(response.json())

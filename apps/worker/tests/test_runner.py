from __future__ import annotations

from typing import Any
from uuid import UUID

from community_llm_protocol import (
    JobArtifactPublic,
    JobAssignment,
    JobPublic,
    WorkerPublic,
)
from community_llm_worker.executor import ArtifactData, ExecutionResult
from community_llm_worker.runner import run_once


class FakeClient:
    def __init__(
        self,
        assignment: JobAssignment | None,
        worker: WorkerPublic,
        artifact: JobArtifactPublic,
        completed: JobPublic,
    ) -> None:
        self.assignment = assignment
        self.worker = worker
        self.artifact = artifact
        self.completed = completed
        self.calls: list[str] = []
        self.fail_calls: list[tuple[str, str]] = []

    def heartbeat(self) -> WorkerPublic:
        self.calls.append("heartbeat")
        return self.worker

    def next_job(self) -> JobAssignment | None:
        self.calls.append("next")
        return self.assignment

    def start(self, attempt_id: UUID | str) -> JobAssignment:
        self.calls.append("start")
        assert self.assignment is not None
        return self.assignment

    def heartbeat_job(self, attempt_id: UUID | str) -> JobAssignment:
        self.calls.append("heartbeat_job")
        assert self.assignment is not None
        return self.assignment

    def upload_artifact(
        self,
        attempt_id: UUID | str,
        name: str,
        data: bytes,
        content_type: str,
    ) -> JobArtifactPublic:
        self.calls.append("upload")
        return self.artifact

    def complete(
        self,
        attempt_id: UUID | str,
        logs: str | None,
        metrics: dict[str, object],
    ) -> JobPublic:
        self.calls.append("complete")
        return self.completed

    def fail(
        self,
        attempt_id: UUID | str,
        error: str,
        logs: str | None = None,
    ) -> JobPublic:
        self.calls.append("fail")
        self.fail_calls.append((error, logs or ""))
        return self.completed


class FakeExecutor:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def execute(self, assignment: JobAssignment) -> ExecutionResult:
        if self.fail:
            raise RuntimeError("boom")
        return ExecutionResult(
            artifacts=[ArtifactData("result.json", b"{}", "application/json")],
            logs="ok",
            metrics={"ok": True},
        )


def _models(
    assignment_payload: dict[str, Any],
    worker_payload: dict[str, Any],
    artifact_payload: dict[str, Any],
    job_payload: dict[str, Any],
) -> tuple[JobAssignment, WorkerPublic, JobArtifactPublic, JobPublic]:
    assignment = JobAssignment.model_validate(assignment_payload)
    worker = WorkerPublic.model_validate(worker_payload)
    artifact = JobArtifactPublic.model_validate(artifact_payload)
    completed = JobPublic.model_validate({**job_payload, "status": "uploaded"})
    return assignment, worker, artifact, completed


def test_run_once(
    assignment_payload: dict[str, Any],
    worker_payload: dict[str, Any],
    artifact_payload: dict[str, Any],
    job_payload: dict[str, Any],
) -> None:
    assignment, worker, artifact, completed = _models(
        assignment_payload, worker_payload, artifact_payload, job_payload
    )
    client = FakeClient(assignment, worker, artifact, completed)

    assert run_once(client, FakeExecutor(), heartbeat_interval=3600) is True
    assert client.calls == [
        "heartbeat",
        "next",
        "start",
        "heartbeat_job",
        "upload",
        "complete",
    ]


def test_run_once_no_job(worker_payload: dict[str, Any]) -> None:
    worker = WorkerPublic.model_validate(worker_payload)
    client = FakeClient(None, worker, None, None)  # type: ignore[arg-type]

    assert run_once(client, FakeExecutor()) is False
    assert client.calls == ["heartbeat", "next"]


def test_run_once_failure(
    assignment_payload: dict[str, Any],
    worker_payload: dict[str, Any],
    artifact_payload: dict[str, Any],
    job_payload: dict[str, Any],
) -> None:
    assignment, worker, artifact, completed = _models(
        assignment_payload, worker_payload, artifact_payload, job_payload
    )
    client = FakeClient(assignment, worker, artifact, completed)

    assert run_once(client, FakeExecutor(fail=True), heartbeat_interval=3600) is False
    assert "fail" in client.calls
    assert client.fail_calls[0][0] == "boom"

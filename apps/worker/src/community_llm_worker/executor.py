from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from community_llm_protocol import JobAssignment


@dataclass(frozen=True)
class ArtifactData:
    name: str
    data: bytes
    content_type: str


@dataclass(frozen=True)
class ExecutionResult:
    artifacts: list[ArtifactData]
    logs: str
    metrics: dict[str, Any]


class Executor(Protocol):
    def execute(self, assignment: JobAssignment) -> ExecutionResult: ...


class FakeGpuExecutor:
    """Deterministic executor for the fake-GPU end-to-end path."""

    def execute(self, assignment: JobAssignment) -> ExecutionResult:
        job = assignment.job
        payload = {
            "attempt_id": str(assignment.attempt.id),
            "job_id": str(job.id),
            "kind": job.kind.value,
            "spec": job.spec,
            "status": "ok",
        }
        data = json.dumps(payload, indent=2, sort_keys=True).encode()
        return ExecutionResult(
            artifacts=[
                ArtifactData(name="result.json", data=data, content_type="application/json")
            ],
            logs=f"fake-gpu: completed {job.kind.value} job {job.id}\n",
            metrics={"fake_gpu": True, "job_kind": job.kind.value},
        )

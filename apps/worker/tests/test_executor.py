from __future__ import annotations

import json
from typing import Any

from community_llm_protocol import JobAssignment
from community_llm_worker.executor import FakeGpuExecutor


def test_fake_gpu_executor(assignment_payload: dict[str, Any]) -> None:
    assignment = JobAssignment.model_validate(assignment_payload)

    result = FakeGpuExecutor().execute(assignment)

    assert len(result.artifacts) == 1
    artifact = result.artifacts[0]
    assert artifact.name == "result.json"
    assert artifact.content_type == "application/json"
    payload = json.loads(artifact.data)
    assert payload["job_id"] == str(assignment.job.id)
    assert payload["kind"] == "eval"
    assert result.metrics["fake_gpu"] is True
    assert "fake-gpu" in result.logs

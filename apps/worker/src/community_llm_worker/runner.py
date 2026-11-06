from __future__ import annotations

import sys
import threading
import time
from typing import Protocol
from uuid import UUID

from community_llm_protocol import (
    JobArtifactPublic,
    JobAssignment,
    JobPublic,
    WorkerPublic,
)

from community_llm_worker.executor import Executor


class WorkerClientLike(Protocol):
    def heartbeat(self) -> WorkerPublic: ...

    def next_job(self) -> JobAssignment | None: ...

    def start(self, attempt_id: UUID | str) -> JobAssignment: ...

    def heartbeat_job(self, attempt_id: UUID | str) -> JobAssignment: ...

    def upload_artifact(
        self,
        attempt_id: UUID | str,
        name: str,
        data: bytes,
        content_type: str,
    ) -> JobArtifactPublic: ...

    def complete(
        self,
        attempt_id: UUID | str,
        logs: str | None,
        metrics: dict[str, object],
    ) -> JobPublic: ...

    def fail(
        self,
        attempt_id: UUID | str,
        error: str,
        logs: str | None = None,
    ) -> JobPublic: ...


class LeaseKeeper:
    def __init__(
        self,
        client: WorkerClientLike,
        attempt_id: UUID | str,
        interval: float,
    ) -> None:
        self._client = client
        self._attempt_id = attempt_id
        self._interval = max(interval, 0.1)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                self._client.heartbeat_job(self._attempt_id)
            except Exception:
                return

    def __enter__(self) -> LeaseKeeper:
        self._thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        self._stop.set()
        self._thread.join(timeout=5)


def run_once(
    client: WorkerClientLike,
    executor: Executor,
    *,
    heartbeat_interval: float = 30.0,
) -> bool:
    client.heartbeat()
    assignment = client.next_job()
    if assignment is None:
        print("No queued jobs.")
        return False

    attempt_id = assignment.attempt.id
    client.start(attempt_id)
    client.heartbeat_job(attempt_id)

    try:
        with LeaseKeeper(client, attempt_id, heartbeat_interval):
            result = executor.execute(assignment)
            for artifact in result.artifacts:
                client.upload_artifact(
                    attempt_id,
                    artifact.name,
                    artifact.data,
                    artifact.content_type,
                )
            job = client.complete(
                attempt_id,
                logs=result.logs,
                metrics=result.metrics,
            )
    except Exception as exc:
        try:
            client.fail(attempt_id, error=str(exc), logs=f"worker error: {exc}")
        except Exception as fail_exc:
            print(f"Failed to report job failure: {fail_exc}", file=sys.stderr)
        print(f"Job failed: {exc}", file=sys.stderr)
        return False

    print(f"Completed job {job.id} ({job.status.value}).")
    return True


def run_loop(
    client: WorkerClientLike,
    executor: Executor,
    *,
    once: bool = False,
    poll_interval: float = 5.0,
    heartbeat_interval: float = 30.0,
) -> None:
    while True:
        ran = run_once(client, executor, heartbeat_interval=heartbeat_interval)
        if once:
            return
        if not ran:
            time.sleep(poll_interval)

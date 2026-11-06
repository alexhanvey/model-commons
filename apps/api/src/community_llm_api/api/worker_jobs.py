from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from community_llm_protocol import (
    JobArtifactPublic,
    JobAssignment,
    JobAttemptPublic,
    JobPublic,
    JobResultPublic,
    JobStatus,
    WorkerJobComplete,
    WorkerJobFail,
)
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from community_llm_api.audit import record_audit_event
from community_llm_api.dependencies import SessionDep, SettingsDep, WorkerDep
from community_llm_api.job_scheduler import (
    assign_next_job,
    extend_lease,
    get_attempt_for_worker,
)
from community_llm_api.job_state import InvalidJobTransition, assert_transition
from community_llm_api.models.artifact import Artifact
from community_llm_api.models.job import Job, JobAttempt
from community_llm_api.redaction import redact_logs

router = APIRouter(prefix="/v1/worker", tags=["worker"])


def _now() -> datetime:
    return datetime.now(UTC)


def _assignment(job: Job, attempt: JobAttempt) -> JobAssignment:
    return JobAssignment(
        job=JobPublic.model_validate(job),
        attempt=JobAttemptPublic.model_validate(attempt),
        lease_expires_at=attempt.lease_expires_at,
    )


@router.post("/jobs/next", response_model=JobAssignment | None)
async def next_job(
    worker: WorkerDep,
    db: SessionDep,
    settings: SettingsDep,
) -> JobAssignment | None:
    return await assign_next_job(db, worker, settings)


@router.post("/jobs/{attempt_id}/start", response_model=JobAssignment)
async def start_job(
    attempt_id: UUID,
    worker: WorkerDep,
    db: SessionDep,
    settings: SettingsDep,
) -> JobAssignment:
    attempt, job = await get_attempt_for_worker(db, attempt_id, worker)

    if attempt.status == "running" and job.status == JobStatus.RUNNING.value:
        return _assignment(job, attempt)
    if attempt.status != "assigned" or job.status != JobStatus.ASSIGNED.value:
        raise HTTPException(status_code=409, detail=f"attempt is {attempt.status}")

    try:
        assert_transition(job.status, JobStatus.RUNNING)
    except InvalidJobTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    now = _now()
    job.status = JobStatus.RUNNING.value
    attempt.status = "running"
    attempt.started_at = now
    extend_lease(attempt, settings, now)
    worker.last_heartbeat_at = now

    await record_audit_event(
        db,
        actor_user_id=None,
        action="job.start",
        target_type="job",
        target_id=job.id,
        data={"attempt": attempt.attempt_number, "worker_id": str(worker.id)},
    )
    await db.commit()
    await db.refresh(job)
    await db.refresh(attempt)
    return _assignment(job, attempt)


@router.post("/jobs/{attempt_id}/heartbeat", response_model=JobAssignment)
async def heartbeat_job(
    attempt_id: UUID,
    worker: WorkerDep,
    db: SessionDep,
    settings: SettingsDep,
) -> JobAssignment:
    attempt, job = await get_attempt_for_worker(db, attempt_id, worker)
    if attempt.status != "running" or job.status != JobStatus.RUNNING.value:
        raise HTTPException(status_code=409, detail=f"attempt is {attempt.status}")

    now = _now()
    extend_lease(attempt, settings, now)
    worker.last_heartbeat_at = now
    await db.commit()
    await db.refresh(attempt)
    return _assignment(job, attempt)


@router.post("/jobs/{attempt_id}/complete", response_model=JobPublic)
async def complete_job(
    attempt_id: UUID,
    payload: WorkerJobComplete,
    worker: WorkerDep,
    db: SessionDep,
) -> JobPublic:
    attempt, job = await get_attempt_for_worker(db, attempt_id, worker)
    if attempt.status != "running" or job.status != JobStatus.RUNNING.value:
        raise HTTPException(status_code=409, detail=f"attempt is {attempt.status}")

    try:
        assert_transition(job.status, JobStatus.UPLOADED)
    except InvalidJobTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    attempt.status = "uploaded"
    attempt.finished_at = _now()
    attempt.logs = redact_logs(payload.logs)
    attempt.metrics = payload.metrics
    job.status = JobStatus.UPLOADED.value

    await record_audit_event(
        db,
        actor_user_id=None,
        action="job.complete",
        target_type="job",
        target_id=job.id,
        data={"attempt": attempt.attempt_number, "worker_id": str(worker.id)},
    )
    await db.commit()
    await db.refresh(job)
    return JobPublic.model_validate(job)


@router.post("/jobs/{attempt_id}/fail", response_model=JobPublic)
async def fail_job(
    attempt_id: UUID,
    payload: WorkerJobFail,
    worker: WorkerDep,
    db: SessionDep,
    settings: SettingsDep,
) -> JobPublic:
    attempt, job = await get_attempt_for_worker(db, attempt_id, worker)
    if attempt.status not in {"assigned", "running"}:
        raise HTTPException(status_code=409, detail=f"attempt is {attempt.status}")

    attempt.status = "failed"
    attempt.finished_at = _now()
    attempt.error = payload.error
    attempt.logs = redact_logs(payload.logs)

    action = "job.attempt_failed"
    if job.status in {JobStatus.ASSIGNED.value, JobStatus.RUNNING.value}:
        try:
            assert_transition(job.status, JobStatus.FAILED)
        except InvalidJobTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        job.status = JobStatus.FAILED.value
        if attempt.attempt_number < settings.max_job_attempts:
            try:
                assert_transition(JobStatus.FAILED, JobStatus.QUEUED)
            except InvalidJobTransition as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            job.status = JobStatus.QUEUED.value
            action = "job.retry"
        else:
            action = "job.fail"

    await record_audit_event(
        db,
        actor_user_id=None,
        action=action,
        target_type="job",
        target_id=job.id,
        data={
            "attempt": attempt.attempt_number,
            "worker_id": str(worker.id),
            "error": payload.error,
        },
    )
    await db.commit()
    await db.refresh(job)
    return JobPublic.model_validate(job)


@router.post(
    "/jobs/{attempt_id}/artifacts",
    response_model=JobArtifactPublic,
    status_code=status.HTTP_201_CREATED,
)
async def upload_artifact(
    attempt_id: UUID,
    worker: WorkerDep,
    db: SessionDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
    expected_sha256: Annotated[str | None, Form()] = None,
) -> JobArtifactPublic:
    attempt, job = await get_attempt_for_worker(db, attempt_id, worker)
    if attempt.status != "running" or job.status != JobStatus.RUNNING.value:
        raise HTTPException(status_code=409, detail=f"attempt is {attempt.status}")

    data = await file.read()
    if len(data) > settings.max_artifact_bytes:
        raise HTTPException(status_code=413, detail="artifact too large")

    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise HTTPException(status_code=422, detail="artifact checksum mismatch")

    name = Path(file.filename or "artifact.bin").name or "artifact.bin"
    path = Path(settings.artifact_dir) / str(job.id) / str(attempt.id) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    artifact = Artifact(
        job_id=job.id,
        name=name,
        uri=f"file://{path}",
        sha256=digest,
        size_bytes=len(data),
        content_type=file.content_type,
    )
    db.add(artifact)
    await db.flush()
    await record_audit_event(
        db,
        actor_user_id=None,
        action="artifact.upload",
        target_type="artifact",
        target_id=artifact.id,
        data={
            "job_id": str(job.id),
            "attempt": attempt.attempt_number,
            "sha256": digest,
            "size_bytes": len(data),
        },
    )
    await db.commit()
    await db.refresh(artifact)
    return JobArtifactPublic.model_validate(artifact)


@router.get("/jobs/{attempt_id}/result", response_model=JobResultPublic)
async def job_result(
    attempt_id: UUID,
    worker: WorkerDep,
    db: SessionDep,
) -> JobResultPublic:
    attempt, _job = await get_attempt_for_worker(db, attempt_id, worker)
    return JobResultPublic(
        logs=attempt.logs,
        metrics=attempt.metrics,
        error=attempt.error,
    )

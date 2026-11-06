from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from community_llm_protocol import (
    JobAssignment,
    JobAttemptPublic,
    JobPublic,
    JobStatus,
)
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from community_llm_api.audit import record_audit_event
from community_llm_api.models.job import Job, JobAttempt
from community_llm_api.models.worker import Worker
from community_llm_api.settings import Settings


def _now() -> datetime:
    return datetime.now(UTC)


def _assignment(job: Job, attempt: JobAttempt) -> JobAssignment:
    return JobAssignment(
        job=JobPublic.model_validate(job),
        attempt=JobAttemptPublic.model_validate(attempt),
        lease_expires_at=attempt.lease_expires_at,
    )


def extend_lease(attempt: JobAttempt, settings: Settings, now: datetime | None = None) -> None:
    attempt.lease_expires_at = (now or _now()) + timedelta(seconds=settings.job_lease_seconds)


async def expire_stale_leases(
    db: AsyncSession,
    settings: Settings,
    now: datetime | None = None,
) -> int:
    current = now or _now()
    result = await db.execute(
        select(JobAttempt, Job)
        .join(Job, Job.id == JobAttempt.job_id)
        .where(
            JobAttempt.status.in_(["assigned", "running"]),
            JobAttempt.lease_expires_at.is_not(None),
            JobAttempt.lease_expires_at < current,
        )
    )
    expired = 0
    for attempt, job in result.all():
        attempt.status = "expired"
        attempt.error = "lease expired"
        attempt.finished_at = current
        expired += 1

        if job.status in {JobStatus.ASSIGNED.value, JobStatus.RUNNING.value}:
            if attempt.attempt_number < settings.max_job_attempts:
                job.status = JobStatus.QUEUED.value
                action = "job.lease_expired_retry"
            else:
                job.status = JobStatus.FAILED.value
                action = "job.lease_expired"
        else:
            action = "job.attempt_expired"

        await record_audit_event(
            db,
            actor_user_id=None,
            action=action,
            target_type="job",
            target_id=job.id,
            data={"attempt": attempt.attempt_number, "worker_id": str(attempt.worker_id)},
        )
    return expired


async def assign_next_job(
    db: AsyncSession,
    worker: Worker,
    settings: Settings,
) -> JobAssignment | None:
    current = _now()
    await expire_stale_leases(db, settings, current)

    result = await db.execute(
        select(Job)
        .where(Job.status == JobStatus.QUEUED.value)
        .order_by(Job.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if job is None:
        await db.commit()
        return None

    last_attempt = await db.scalar(
        select(func.max(JobAttempt.attempt_number)).where(JobAttempt.job_id == job.id)
    )
    attempt = JobAttempt(
        job_id=job.id,
        attempt_number=int(last_attempt or 0) + 1,
        worker_id=worker.id,
        status="assigned",
        lease_expires_at=current + timedelta(seconds=settings.job_lease_seconds),
    )
    job.status = JobStatus.ASSIGNED.value
    db.add(attempt)
    await db.flush()
    await record_audit_event(
        db,
        actor_user_id=None,
        action="job.assign",
        target_type="job",
        target_id=job.id,
        data={"worker_id": str(worker.id), "attempt": attempt.attempt_number},
    )
    await db.commit()
    await db.refresh(job)
    await db.refresh(attempt)
    return _assignment(job, attempt)


async def get_attempt_for_worker(
    db: AsyncSession,
    attempt_id: UUID,
    worker: Worker,
) -> tuple[JobAttempt, Job]:
    result = await db.execute(
        select(JobAttempt, Job)
        .join(Job, Job.id == JobAttempt.job_id)
        .where(JobAttempt.id == attempt_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="job attempt not found")
    attempt, job = row
    if attempt.worker_id != worker.id:
        raise HTTPException(status_code=404, detail="job attempt not found")
    return attempt, job

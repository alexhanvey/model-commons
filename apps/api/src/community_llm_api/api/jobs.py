from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from community_llm_protocol import JobCreate, JobPublic, JobStatus
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from community_llm_api.audit import record_audit_event
from community_llm_api.dependencies import CsrfContextDep, SessionContextDep, SessionDep
from community_llm_api.job_state import InvalidJobTransition, assert_transition
from community_llm_api.models.job import Job
from community_llm_api.models.user import User

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


async def _get_job(db: AsyncSession, job_id: UUID, user: User) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None or (not user.is_admin and job.user_id != user.id):
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("", response_model=JobPublic, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    context: CsrfContextDep,
    db: SessionDep,
) -> JobPublic:
    job = Job(
        user_id=context.user.id,
        kind=payload.kind.value,
        status=JobStatus.QUEUED.value,
        spec=payload.spec,
    )
    db.add(job)
    await db.flush()
    await record_audit_event(
        db,
        actor_user_id=context.user.id,
        action="job.create",
        target_type="job",
        target_id=job.id,
        data={"kind": payload.kind.value},
    )
    await db.commit()
    await db.refresh(job)
    return JobPublic.model_validate(job)


@router.get("", response_model=list[JobPublic])
async def list_jobs(
    context: SessionContextDep,
    db: SessionDep,
) -> list[JobPublic]:
    query = select(Job).order_by(Job.created_at.desc())
    if not context.user.is_admin:
        query = query.where(Job.user_id == context.user.id)
    result = await db.execute(query)
    return [JobPublic.model_validate(job) for job in result.scalars()]


@router.get("/{job_id}", response_model=JobPublic)
async def get_job(
    job_id: UUID,
    context: SessionContextDep,
    db: SessionDep,
) -> JobPublic:
    job = await _get_job(db, job_id, context.user)
    return JobPublic.model_validate(job)


@router.post("/{job_id}/cancel", response_model=JobPublic)
async def cancel_job(
    job_id: UUID,
    context: CsrfContextDep,
    db: SessionDep,
) -> JobPublic:
    job = await _get_job(db, job_id, context.user)
    previous_status = job.status
    try:
        assert_transition(previous_status, JobStatus.CANCELLED)
    except InvalidJobTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    job.status = JobStatus.CANCELLED.value
    job.cancelled_at = datetime.now(UTC)
    await record_audit_event(
        db,
        actor_user_id=context.user.id,
        action="job.cancel",
        target_type="job",
        target_id=job.id,
        data={"from": previous_status, "to": JobStatus.CANCELLED.value},
    )
    await db.commit()
    await db.refresh(job)
    return JobPublic.model_validate(job)

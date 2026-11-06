from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from community_llm_protocol import (
    AdminGrantCreate,
    AdminGrantResponse,
    JobPublic,
    JobStatus,
    LedgerReconciliation,
)
from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from community_llm_api.audit import record_audit_event
from community_llm_api.dependencies import AdminContextDep, AdminCsrfContextDep, SessionDep
from community_llm_api.job_rewards import reward_for
from community_llm_api.job_state import InvalidJobTransition, assert_transition
from community_llm_api.ledger import (
    LedgerError,
    get_user_points,
    grant_points,
    reconcile_ledger,
)
from community_llm_api.models.artifact import Artifact
from community_llm_api.models.job import Job
from community_llm_api.models.user import User

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.post("/grants", response_model=AdminGrantResponse)
async def create_grant(
    payload: AdminGrantCreate,
    context: AdminCsrfContextDep,
    db: SessionDep,
) -> AdminGrantResponse:
    user = await db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    try:
        transaction = await grant_points(
            db,
            user_id=payload.user_id,
            amount=payload.amount,
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
            actor_user_id=context.user.id,
        )
    except LedgerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    await record_audit_event(
        db,
        actor_user_id=context.user.id,
        action="ledger.grant",
        target_type="ledger_transaction",
        target_id=transaction.id,
        data={
            "user_id": str(payload.user_id),
            "amount": payload.amount,
            "reason": payload.reason,
        },
    )
    await db.commit()

    available, _ = await get_user_points(db, payload.user_id)
    return AdminGrantResponse(transaction_id=transaction.id, available=available)


@router.get("/ledger/reconciliation", response_model=LedgerReconciliation)
async def ledger_reconciliation(
    context: AdminContextDep,
    db: SessionDep,
) -> LedgerReconciliation:
    result = await reconcile_ledger(db)
    return LedgerReconciliation.model_validate(asdict(result))


async def _get_admin_job(db: SessionDep, job_id: UUID) -> Job:
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/jobs/{job_id}/verify", response_model=JobPublic)
async def verify_job(
    job_id: UUID,
    context: AdminCsrfContextDep,
    db: SessionDep,
) -> JobPublic:
    job = await _get_admin_job(db, job_id)

    if job.status == JobStatus.PAID.value:
        raise HTTPException(status_code=409, detail="job already paid")
    if job.status == JobStatus.VERIFIED.value:
        try:
            assert_transition(JobStatus.VERIFIED, JobStatus.PAID)
        except InvalidJobTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        job.status = JobStatus.PAID.value
        await record_audit_event(
            db,
            actor_user_id=context.user.id,
            action="job.pay",
            target_type="job",
            target_id=job.id,
            data={"kind": job.kind, "reward": reward_for(job.kind)},
        )
        await db.commit()
        await db.refresh(job)
        return JobPublic.model_validate(job)
    if job.status != JobStatus.UPLOADED.value:
        raise HTTPException(status_code=409, detail=f"job is {job.status}, not uploaded")

    artifact_count = await db.scalar(
        select(func.count()).select_from(Artifact).where(Artifact.job_id == job.id)
    )
    if not artifact_count:
        raise HTTPException(status_code=422, detail="job has no artifacts")

    try:
        assert_transition(job.status, JobStatus.VERIFIED)
    except InvalidJobTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    reward = reward_for(job.kind)
    job.status = JobStatus.VERIFIED.value
    try:
        await grant_points(
            db,
            user_id=job.user_id,
            amount=reward,
            reason=f"job reward: {job.kind}",
            idempotency_key=f"job:{job.id}:reward",
            actor_user_id=context.user.id,
        )
    except LedgerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job.status = JobStatus.PAID.value
    await record_audit_event(
        db,
        actor_user_id=context.user.id,
        action="job.verify",
        target_type="job",
        target_id=job.id,
        data={"kind": job.kind, "reward": reward},
    )
    await db.commit()
    await db.refresh(job)
    return JobPublic.model_validate(job)


@router.post("/jobs/{job_id}/reject", response_model=JobPublic)
async def reject_job(
    job_id: UUID,
    context: AdminCsrfContextDep,
    db: SessionDep,
) -> JobPublic:
    job = await _get_admin_job(db, job_id)
    if job.status != JobStatus.UPLOADED.value:
        raise HTTPException(status_code=409, detail=f"job is {job.status}, not uploaded")

    try:
        assert_transition(job.status, JobStatus.REJECTED)
    except InvalidJobTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    job.status = JobStatus.REJECTED.value
    await record_audit_event(
        db,
        actor_user_id=context.user.id,
        action="job.reject",
        target_type="job",
        target_id=job.id,
        data={"kind": job.kind},
    )
    await db.commit()
    await db.refresh(job)
    return JobPublic.model_validate(job)

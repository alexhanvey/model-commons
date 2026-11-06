from __future__ import annotations

import secrets
from datetime import UTC, datetime
from uuid import UUID

from community_llm_protocol import WorkerCreate, WorkerCreated, WorkerPublic
from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from community_llm_api.dependencies import (
    AdminCsrfContextDep,
    CsrfContextDep,
    SessionContextDep,
    SessionDep,
    WorkerDep,
    hash_token,
)
from community_llm_api.models.worker import Worker

router = APIRouter(prefix="/v1/workers", tags=["workers"])


@router.post("", response_model=WorkerCreated, status_code=status.HTTP_201_CREATED)
async def create_worker(
    payload: WorkerCreate,
    context: CsrfContextDep,
    db: SessionDep,
) -> WorkerCreated:
    token = f"wrk_{secrets.token_urlsafe(32)}"
    worker = Worker(
        user_id=context.user.id,
        name=payload.name,
        token_prefix=token[:12],
        token_hash=hash_token(token),
        status="pending",
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)
    return WorkerCreated(worker=WorkerPublic.model_validate(worker), token=token)


@router.get("", response_model=list[WorkerPublic])
async def list_workers(
    context: SessionContextDep,
    db: SessionDep,
) -> list[WorkerPublic]:
    query = select(Worker).order_by(Worker.created_at.desc())
    if not context.user.is_admin:
        query = query.where(Worker.user_id == context.user.id)
    result = await db.execute(query)
    return [WorkerPublic.model_validate(worker) for worker in result.scalars()]


@router.post("/{worker_id}/approve", response_model=WorkerPublic)
async def approve_worker(
    worker_id: UUID,
    context: AdminCsrfContextDep,
    db: SessionDep,
) -> WorkerPublic:
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if worker is None:
        raise HTTPException(status_code=404, detail="worker not found")
    if worker.status == "revoked":
        raise HTTPException(status_code=409, detail="worker is revoked")

    if worker.status != "approved":
        worker.status = "approved"
        worker.approved_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(worker)

    return WorkerPublic.model_validate(worker)


@router.delete("/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_worker(
    worker_id: UUID,
    context: CsrfContextDep,
    db: SessionDep,
) -> Response:
    query = select(Worker).where(Worker.id == worker_id)
    if not context.user.is_admin:
        query = query.where(Worker.user_id == context.user.id)

    result = await db.execute(query)
    worker = result.scalar_one_or_none()
    if worker is None:
        raise HTTPException(status_code=404, detail="worker not found")

    if worker.status != "revoked":
        worker.status = "revoked"
        await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/heartbeat", response_model=WorkerPublic)
async def heartbeat(worker: WorkerDep, db: SessionDep) -> WorkerPublic:
    worker.last_heartbeat_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(worker)
    return WorkerPublic.model_validate(worker)

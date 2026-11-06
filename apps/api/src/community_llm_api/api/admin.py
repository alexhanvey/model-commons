from __future__ import annotations

from dataclasses import asdict

from community_llm_protocol import (
    AdminGrantCreate,
    AdminGrantResponse,
    LedgerReconciliation,
)
from fastapi import APIRouter, HTTPException

from community_llm_api.audit import record_audit_event
from community_llm_api.dependencies import AdminContextDep, AdminCsrfContextDep, SessionDep
from community_llm_api.ledger import (
    LedgerError,
    get_user_points,
    grant_points,
    reconcile_ledger,
)
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

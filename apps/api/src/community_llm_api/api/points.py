from __future__ import annotations

from community_llm_protocol import (
    LedgerEntryPublic,
    LedgerTransactionPublic,
    PointsBalance,
)
from fastapi import APIRouter

from community_llm_api.dependencies import SessionContextDep, SessionDep
from community_llm_api.ledger import get_user_points, list_user_transactions

router = APIRouter(prefix="/v1/points", tags=["points"])


@router.get("/balance", response_model=PointsBalance)
async def get_balance(
    context: SessionContextDep,
    db: SessionDep,
) -> PointsBalance:
    available, held = await get_user_points(db, context.user.id)
    return PointsBalance(available=available, held=held)


@router.get("/transactions", response_model=list[LedgerTransactionPublic])
async def get_transactions(
    context: SessionContextDep,
    db: SessionDep,
) -> list[LedgerTransactionPublic]:
    transactions = await list_user_transactions(db, context.user.id)
    return [
        LedgerTransactionPublic.model_validate(
            {
                "id": transaction.id,
                "type": transaction.type,
                "description": transaction.description,
                "created_at": transaction.created_at,
                "entries": [
                    LedgerEntryPublic.model_validate(
                        {
                            "account": entry.account.code,
                            "direction": entry.direction,
                            "amount": entry.amount,
                        }
                    )
                    for entry in transaction.entries
                ],
            }
        )
        for transaction in transactions
    ]

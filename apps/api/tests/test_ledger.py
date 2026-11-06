from __future__ import annotations

import asyncio
import random
from uuid import UUID

import pytest
from community_llm_api.ledger import (
    EntryInput,
    InsufficientBalance,
    InvalidLedgerTransaction,
    ensure_account,
    get_user_points,
    grant_points,
    reconcile_ledger,
    spend_points,
    user_available_code,
    validate_entries,
)
from community_llm_api.models.audit import AuditEvent
from community_llm_api.models.ledger import LedgerEntry, LedgerTransaction
from fastapi.testclient import TestClient
from sqlalchemy import func, select


def _user_id(client: TestClient) -> str:
    response = client.get("/v1/me")
    assert response.status_code == 200
    return str(response.json()["user"]["id"])


def test_grant_balance_transactions_and_idempotency(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    user_id = _user_id(signed_in_client)
    payload = {
        "user_id": user_id,
        "amount": 100,
        "reason": "test grant",
        "idempotency_key": "grant-1",
    }

    granted = signed_in_client.post(
        "/v1/admin/grants",
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert granted.status_code == 200
    assert granted.json()["available"] == 100

    balance = signed_in_client.get("/v1/points/balance")
    assert balance.status_code == 200
    assert balance.json() == {"available": 100, "held": 0}

    transactions = signed_in_client.get("/v1/points/transactions")
    assert transactions.status_code == 200
    body = transactions.json()
    assert len(body) == 1
    assert body[0]["type"] == "grant"
    assert len(body[0]["entries"]) == 2
    assert {entry["direction"] for entry in body[0]["entries"]} == {"debit", "credit"}
    assert sum(entry["amount"] for entry in body[0]["entries"]) == 200

    replay = signed_in_client.post(
        "/v1/admin/grants",
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert replay.status_code == 200
    assert replay.json()["transaction_id"] == granted.json()["transaction_id"]
    assert replay.json()["available"] == 100
    assert len(signed_in_client.get("/v1/points/transactions").json()) == 1


def test_grant_requires_csrf(signed_in_client: TestClient) -> None:
    response = signed_in_client.post(
        "/v1/admin/grants",
        json={
            "user_id": _user_id(signed_in_client),
            "amount": 10,
            "reason": "test",
            "idempotency_key": "no-csrf",
        },
    )
    assert response.status_code == 403


def test_grant_rejects_unknown_user(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    response = signed_in_client.post(
        "/v1/admin/grants",
        json={
            "user_id": "00000000-0000-0000-0000-000000000000",
            "amount": 10,
            "reason": "test",
            "idempotency_key": "unknown-user",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 404


def test_spend_and_insufficient_balance(
    signed_in_client: TestClient,
    csrf_token: str,
    session_factory,
) -> None:
    user_id = UUID(_user_id(signed_in_client))
    granted = signed_in_client.post(
        "/v1/admin/grants",
        json={
            "user_id": str(user_id),
            "amount": 50,
            "reason": "seed",
            "idempotency_key": "spend-seed",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert granted.status_code == 200

    async def spend() -> tuple[int, int]:
        async with session_factory() as session:
            await spend_points(
                session,
                user_id=user_id,
                amount=20,
                description="test spend",
                idempotency_key="spend-1",
            )
        async with session_factory() as session:
            return await get_user_points(session, user_id)

    available, held = asyncio.run(spend())
    assert (available, held) == (30, 0)

    async def overspend() -> None:
        async with session_factory() as session:
            await spend_points(
                session,
                user_id=user_id,
                amount=100,
                description="too much",
                idempotency_key="spend-2",
            )

    with pytest.raises(InsufficientBalance):
        asyncio.run(overspend())


def test_unbalanced_entries_are_rejected() -> None:
    entries = [
        EntryInput("system_issued", "debit", 10),
        EntryInput("user_available:00000000-0000-0000-0000-000000000000", "credit", 9),
    ]
    with pytest.raises(InvalidLedgerTransaction):
        validate_entries(entries)


def test_random_ledger_sequence(
    signed_in_client: TestClient,
    csrf_token: str,
    session_factory,
) -> None:
    user_id = UUID(_user_id(signed_in_client))
    seed = signed_in_client.post(
        "/v1/admin/grants",
        json={
            "user_id": str(user_id),
            "amount": 1000,
            "reason": "seed",
            "idempotency_key": "random-seed",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert seed.status_code == 200

    rng = random.Random(42)
    expected = 1000

    async def run() -> tuple[int, int]:
        nonlocal expected
        for index in range(40):
            async with session_factory() as session:
                if expected == 0 or rng.random() < 0.4:
                    amount = rng.randint(1, 50)
                    await grant_points(
                        session,
                        user_id=user_id,
                        amount=amount,
                        reason="random grant",
                        idempotency_key=f"random-grant-{index}",
                        actor_user_id=user_id,
                    )
                    expected += amount
                else:
                    amount = rng.randint(1, min(50, expected))
                    await spend_points(
                        session,
                        user_id=user_id,
                        amount=amount,
                        description="random spend",
                        idempotency_key=f"random-spend-{index}",
                    )
                    expected -= amount
        async with session_factory() as session:
            return await get_user_points(session, user_id)

    available, held = asyncio.run(run())
    assert available == expected
    assert available >= 0
    assert held == 0


def test_audit_event_is_written(
    signed_in_client: TestClient,
    csrf_token: str,
    session_factory,
) -> None:
    user_id = _user_id(signed_in_client)
    response = signed_in_client.post(
        "/v1/admin/grants",
        json={
            "user_id": user_id,
            "amount": 5,
            "reason": "audit",
            "idempotency_key": "audit-grant",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 200

    async def count() -> int:
        async with session_factory() as session:
            result = await session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.action == "ledger.grant")
            )
            return int(result or 0)

    assert asyncio.run(count()) >= 1


def test_reconciliation_ok_and_admin_endpoint(
    signed_in_client: TestClient,
    csrf_token: str,
    session_factory,
) -> None:
    user_id = _user_id(signed_in_client)
    granted = signed_in_client.post(
        "/v1/admin/grants",
        json={
            "user_id": user_id,
            "amount": 20,
            "reason": "reconcile",
            "idempotency_key": "reconcile-grant",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert granted.status_code == 200

    response = signed_in_client.get("/v1/admin/ledger/reconciliation")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["transactions"] == 1
    assert body["unbalanced_transactions"] == 0
    assert body["negative_accounts"] == 0
    assert body["total_debits"] == 20
    assert body["total_credits"] == 20

    async def check():
        async with session_factory() as session:
            return await reconcile_ledger(session)

    result = asyncio.run(check())
    assert result.ok is True


def test_reconciliation_detects_unbalanced_transaction(
    signed_in_client: TestClient,
    csrf_token: str,
    session_factory,
) -> None:
    user_id = UUID(_user_id(signed_in_client))
    granted = signed_in_client.post(
        "/v1/admin/grants",
        json={
            "user_id": str(user_id),
            "amount": 10,
            "reason": "seed",
            "idempotency_key": "reconcile-bad-seed",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert granted.status_code == 200

    async def insert_bad() -> None:
        async with session_factory() as session:
            account = await ensure_account(session, user_available_code(user_id))
            transaction = LedgerTransaction(type="adjustment", description="unbalanced")
            session.add(transaction)
            await session.flush()
            session.add(
                LedgerEntry(
                    transaction_id=transaction.id,
                    account_id=account.id,
                    direction="credit",
                    amount=5,
                )
            )
            await session.commit()

    asyncio.run(insert_bad())

    async def check():
        async with session_factory() as session:
            return await reconcile_ledger(session)

    result = asyncio.run(check())
    assert result.ok is False
    assert result.unbalanced_transactions >= 1
    assert result.total_debits != result.total_credits

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from community_llm_protocol import LedgerTransactionType
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from community_llm_api.models.ledger import LedgerAccount, LedgerEntry, LedgerTransaction

Direction = Literal["debit", "credit"]

SYSTEM_ISSUED = "system_issued"
SYSTEM_REVENUE = "system_revenue"


class LedgerError(ValueError):
    """Base class for ledger domain errors."""


class InvalidLedgerTransaction(LedgerError):
    """Raised when entries are unbalanced or malformed."""


class InsufficientBalance(LedgerError):
    """Raised when a user account would go negative."""


class AccountNotFound(LedgerError):
    """Raised when an unknown ledger account code is used."""


@dataclass(frozen=True)
class EntryInput:
    account: str
    direction: Direction
    amount: int


def user_available_code(user_id: UUID) -> str:
    return f"user_available:{user_id}"


def user_held_code(user_id: UUID) -> str:
    return f"user_held:{user_id}"


def validate_entries(entries: list[EntryInput]) -> None:
    if not entries:
        raise InvalidLedgerTransaction("transaction has no entries")

    seen: set[tuple[str, str]] = set()
    debits = 0
    credits = 0

    for entry in entries:
        if entry.amount <= 0:
            raise InvalidLedgerTransaction("entry amounts must be positive")
        if entry.direction not in {"debit", "credit"}:
            raise InvalidLedgerTransaction("entry direction must be debit or credit")
        key = (entry.account, entry.direction)
        if key in seen:
            raise InvalidLedgerTransaction("duplicate account and direction in transaction")
        seen.add(key)
        if entry.direction == "debit":
            debits += entry.amount
        else:
            credits += entry.amount

    if debits != credits:
        raise InvalidLedgerTransaction("debits must equal credits")


async def get_account_by_code(db: AsyncSession, code: str) -> LedgerAccount | None:
    return await db.scalar(select(LedgerAccount).where(LedgerAccount.code == code))


async def ensure_account(db: AsyncSession, code: str) -> LedgerAccount:
    existing = await get_account_by_code(db, code)
    if existing is not None:
        return existing

    kind, _, subject = code.partition(":")
    if kind in {"user_available", "user_held"}:
        if not subject:
            raise AccountNotFound(code)
        try:
            user_id = UUID(subject)
        except ValueError as exc:
            raise AccountNotFound(code) from exc
        account = LedgerAccount(code=code, kind=kind, user_id=user_id)
    elif kind in {SYSTEM_ISSUED, SYSTEM_REVENUE} and not subject:
        account = LedgerAccount(code=code, kind=kind)
    else:
        raise AccountNotFound(code)

    db.add(account)
    await db.flush()
    return account


async def get_account_balance(db: AsyncSession, account_id: UUID) -> int:
    result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (LedgerEntry.direction == "credit", LedgerEntry.amount),
                        else_=-LedgerEntry.amount,
                    )
                ),
                0,
            )
        ).where(LedgerEntry.account_id == account_id)
    )
    return int(result.scalar_one())


async def get_user_balance(
    db: AsyncSession,
    user_id: UUID,
    kind: Literal["user_available", "user_held"] = "user_available",
) -> int:
    code = user_available_code(user_id) if kind == "user_available" else user_held_code(user_id)
    account = await get_account_by_code(db, code)
    if account is None:
        return 0
    return await get_account_balance(db, account.id)


async def get_user_points(db: AsyncSession, user_id: UUID) -> tuple[int, int]:
    available = await get_user_balance(db, user_id, "user_available")
    held = await get_user_balance(db, user_id, "user_held")
    return available, held


async def get_transaction_by_idempotency_key(
    db: AsyncSession,
    idempotency_key: str,
) -> LedgerTransaction | None:
    return await db.scalar(
        select(LedgerTransaction).where(LedgerTransaction.idempotency_key == idempotency_key)
    )


async def post_transaction(
    db: AsyncSession,
    *,
    transaction_type: LedgerTransactionType,
    entries: list[EntryInput],
    idempotency_key: str | None = None,
    description: str | None = None,
    created_by_user_id: UUID | None = None,
    require_non_negative: frozenset[str] | None = None,
) -> LedgerTransaction:
    validate_entries(entries)

    if idempotency_key:
        existing = await get_transaction_by_idempotency_key(db, idempotency_key)
        if existing is not None:
            return existing

    accounts: dict[str, LedgerAccount] = {}
    for code in sorted({entry.account for entry in entries}):
        accounts[code] = await ensure_account(db, code)

    for code in sorted(accounts):
        locked = await db.scalar(
            select(LedgerAccount).where(LedgerAccount.code == code).with_for_update()
        )
        if locked is None:
            raise AccountNotFound(code)
        accounts[code] = locked

    for code in require_non_negative or frozenset():
        account = accounts.get(code)
        if account is None:
            raise AccountNotFound(code)
        debit = sum(
            entry.amount
            for entry in entries
            if entry.account == code and entry.direction == "debit"
        )
        if debit and await get_account_balance(db, account.id) < debit:
            raise InsufficientBalance(code)

    transaction = LedgerTransaction(
        type=transaction_type.value,
        idempotency_key=idempotency_key,
        description=description,
        created_by_user_id=created_by_user_id,
    )
    db.add(transaction)
    await db.flush()

    for entry in entries:
        db.add(
            LedgerEntry(
                transaction_id=transaction.id,
                account_id=accounts[entry.account].id,
                direction=entry.direction,
                amount=entry.amount,
            )
        )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        if idempotency_key:
            existing = await get_transaction_by_idempotency_key(db, idempotency_key)
            if existing is not None:
                return existing
        raise

    await db.refresh(transaction)
    return transaction


async def grant_points(
    db: AsyncSession,
    *,
    user_id: UUID,
    amount: int,
    reason: str,
    idempotency_key: str,
    actor_user_id: UUID,
) -> LedgerTransaction:
    if amount <= 0:
        raise InvalidLedgerTransaction("grant amount must be positive")

    available = user_available_code(user_id)
    await ensure_account(db, available)
    await ensure_account(db, SYSTEM_ISSUED)

    return await post_transaction(
        db,
        transaction_type=LedgerTransactionType.GRANT,
        entries=[
            EntryInput(account=SYSTEM_ISSUED, direction="debit", amount=amount),
            EntryInput(account=available, direction="credit", amount=amount),
        ],
        idempotency_key=idempotency_key,
        description=reason,
        created_by_user_id=actor_user_id,
    )


async def spend_points(
    db: AsyncSession,
    *,
    user_id: UUID,
    amount: int,
    description: str,
    idempotency_key: str | None = None,
) -> LedgerTransaction:
    if amount <= 0:
        raise InvalidLedgerTransaction("spend amount must be positive")

    available = user_available_code(user_id)
    await ensure_account(db, available)
    await ensure_account(db, SYSTEM_REVENUE)

    return await post_transaction(
        db,
        transaction_type=LedgerTransactionType.SPEND,
        entries=[
            EntryInput(account=available, direction="debit", amount=amount),
            EntryInput(account=SYSTEM_REVENUE, direction="credit", amount=amount),
        ],
        idempotency_key=idempotency_key,
        description=description,
        require_non_negative=frozenset({available}),
    )


async def list_user_transactions(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 50,
) -> list[LedgerTransaction]:
    account = await get_account_by_code(db, user_available_code(user_id))
    if account is None:
        return []

    result = await db.execute(
        select(LedgerTransaction)
        .join(LedgerEntry, LedgerEntry.transaction_id == LedgerTransaction.id)
        .where(LedgerEntry.account_id == account.id)
        .order_by(LedgerTransaction.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().unique())


@dataclass(frozen=True)
class ReconciliationResult:
    ok: bool
    transactions: int
    unbalanced_transactions: int
    negative_accounts: int
    total_debits: int
    total_credits: int


async def reconcile_ledger(db: AsyncSession) -> ReconciliationResult:
    transaction_count = int(
        await db.scalar(select(func.count()).select_from(LedgerTransaction)) or 0
    )

    totals = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (LedgerEntry.direction == "debit", LedgerEntry.amount),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (LedgerEntry.direction == "credit", LedgerEntry.amount),
                        else_=0,
                    )
                ),
                0,
            ),
        )
    )
    total_debits, total_credits = totals.one()

    rows = await db.execute(
        select(
            LedgerTransaction.id,
            func.coalesce(
                func.sum(
                    case(
                        (LedgerEntry.direction == "debit", LedgerEntry.amount),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (LedgerEntry.direction == "credit", LedgerEntry.amount),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .outerjoin(LedgerEntry, LedgerEntry.transaction_id == LedgerTransaction.id)
        .group_by(LedgerTransaction.id)
    )
    unbalanced = sum(1 for _, debits, credits in rows.all() if debits != credits)

    accounts = await db.execute(
        select(LedgerAccount.id).where(LedgerAccount.kind == "user_available")
    )
    negative_accounts = 0
    for account_id in accounts.scalars():
        if await get_account_balance(db, account_id) < 0:
            negative_accounts += 1

    return ReconciliationResult(
        ok=(unbalanced == 0 and negative_accounts == 0 and total_debits == total_credits),
        transactions=transaction_count,
        unbalanced_transactions=unbalanced,
        negative_accounts=negative_accounts,
        total_debits=int(total_debits or 0),
        total_credits=int(total_credits or 0),
    )

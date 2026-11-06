from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from community_llm_api.models.base import Base


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100), unique=True, index=True, nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    entries: Mapped[list[LedgerEntry]] = relationship(
        back_populates="transaction",
        lazy="selectin",
    )


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        UniqueConstraint(
            "transaction_id",
            "account_id",
            "direction",
            name="uq_ledger_entries_transaction_account_direction",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("ledger_transactions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("ledger_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    transaction: Mapped[LedgerTransaction] = relationship(back_populates="entries")
    account: Mapped[LedgerAccount] = relationship(lazy="joined")

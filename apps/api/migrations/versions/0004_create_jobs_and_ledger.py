"""create jobs and ledger

Revision ID: 0004_create_jobs_and_ledger
Revises: 0003_create_api_keys_and_workers
Create Date: 2026-11-06

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_create_jobs_and_ledger"
down_revision = "0003_create_api_keys_and_workers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="queued", nullable=False),
        sa.Column("spec", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_jobs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)
    op.create_index(op.f("ix_jobs_user_id"), "jobs", ["user_id"], unique=False)

    op.create_table(
        "job_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="assigned", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name=op.f("fk_job_attempts_job_id_jobs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worker_id"],
            ["workers.id"],
            name=op.f("fk_job_attempts_worker_id_workers"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_attempts")),
        sa.UniqueConstraint(
            "job_id",
            "attempt_number",
            name="uq_job_attempts_job_id_attempt_number",
        ),
    )
    op.create_index(op.f("ix_job_attempts_job_id"), "job_attempts", ["job_id"], unique=False)
    op.create_index(op.f("ix_job_attempts_worker_id"), "job_attempts", ["worker_id"], unique=False)

    op.create_table(
        "ledger_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_ledger_accounts_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_accounts")),
    )
    op.create_index(op.f("ix_ledger_accounts_code"), "ledger_accounts", ["code"], unique=True)
    op.create_index(op.f("ix_ledger_accounts_kind"), "ledger_accounts", ["kind"], unique=False)
    op.create_index(
        op.f("ix_ledger_accounts_user_id"), "ledger_accounts", ["user_id"], unique=False
    )

    op.create_table(
        "ledger_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_ledger_transactions_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_transactions")),
    )
    op.create_index(
        op.f("ix_ledger_transactions_created_by_user_id"),
        "ledger_transactions",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ledger_transactions_idempotency_key"),
        "ledger_transactions",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(op.f("ix_ledger_transactions_type"), "ledger_transactions", ["type"])

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["ledger_accounts.id"],
            name=op.f("fk_ledger_entries_account_id_ledger_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["ledger_transactions.id"],
            name=op.f("fk_ledger_entries_transaction_id_ledger_transactions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_entries")),
        sa.UniqueConstraint(
            "transaction_id",
            "account_id",
            "direction",
            name="uq_ledger_entries_transaction_account_direction",
        ),
    )
    op.create_index(
        op.f("ix_ledger_entries_account_id"), "ledger_entries", ["account_id"], unique=False
    )
    op.create_index(
        op.f("ix_ledger_entries_transaction_id"),
        "ledger_entries",
        ["transaction_id"],
        unique=False,
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_audit_events_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(op.f("ix_audit_events_action"), "audit_events", ["action"], unique=False)
    op.create_index(
        op.f("ix_audit_events_actor_user_id"),
        "audit_events",
        ["actor_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_events_actor_user_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_action"), table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index(op.f("ix_ledger_entries_transaction_id"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_account_id"), table_name="ledger_entries")
    op.drop_table("ledger_entries")

    op.drop_index(op.f("ix_ledger_transactions_type"), table_name="ledger_transactions")
    op.drop_index(op.f("ix_ledger_transactions_idempotency_key"), table_name="ledger_transactions")
    op.drop_index(
        op.f("ix_ledger_transactions_created_by_user_id"),
        table_name="ledger_transactions",
    )
    op.drop_table("ledger_transactions")

    op.drop_index(op.f("ix_ledger_accounts_user_id"), table_name="ledger_accounts")
    op.drop_index(op.f("ix_ledger_accounts_kind"), table_name="ledger_accounts")
    op.drop_index(op.f("ix_ledger_accounts_code"), table_name="ledger_accounts")
    op.drop_table("ledger_accounts")

    op.drop_index(op.f("ix_job_attempts_worker_id"), table_name="job_attempts")
    op.drop_index(op.f("ix_job_attempts_job_id"), table_name="job_attempts")
    op.drop_table("job_attempts")

    op.drop_index(op.f("ix_jobs_user_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
    op.drop_table("jobs")

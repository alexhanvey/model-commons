"""add worker lease and result fields

Revision ID: 0006_job_attempt_lease
Revises: 0005_create_phase2_scaffolding
Create Date: 2026-11-06

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_job_attempt_lease"
down_revision = "0005_create_phase2_scaffolding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_attempts",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("job_attempts", sa.Column("logs", sa.Text(), nullable=True))
    op.add_column("job_attempts", sa.Column("metrics", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("job_attempts", "metrics")
    op.drop_column("job_attempts", "logs")
    op.drop_column("job_attempts", "lease_expires_at")

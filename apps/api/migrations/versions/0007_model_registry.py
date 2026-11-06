"""add model registry and job recipe refs

Revision ID: 0007_model_registry
Revises: 0006_job_attempt_lease
Create Date: 2026-11-06

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_model_registry"
down_revision = "0006_job_attempt_lease"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("recipe_ref", sa.JSON(), nullable=True))

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("base_model", sa.String(length=200), nullable=False),
        sa.Column("base_revision", sa.String(length=64), nullable=False),
        sa.Column("recipe_ref", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="candidate", nullable=False),
        sa.Column("adapter_uri", sa.String(length=500), nullable=False),
        sa.Column("adapter_sha256", sa.String(length=64), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("model_card", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_model_versions_created_by_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_versions")),
        sa.UniqueConstraint("name", "version", name="uq_model_versions_name_version"),
    )
    op.create_index(
        op.f("ix_model_versions_created_by_user_id"),
        "model_versions",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_versions_status"),
        "model_versions",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_model_versions_status"), table_name="model_versions")
    op.drop_index(op.f("ix_model_versions_created_by_user_id"), table_name="model_versions")
    op.drop_table("model_versions")
    op.drop_column("jobs", "recipe_ref")

"""Add audit-only shadow agent run traces.

Revision ID: 20261005_0015
Revises: 20261004_0014
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261005_0015"
down_revision: str | None = "20261004_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shadow_agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("recommendation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trajectory", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("termination_reason", sa.String(length=120), nullable=False),
        sa.Column("used_fallback", sa.Boolean(), nullable=False),
        sa.Column("business_writes", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shadow_agent_runs_user_id", "shadow_agent_runs", ["user_id"])
    op.create_index(
        "ix_shadow_agent_runs_knowledge_base_id",
        "shadow_agent_runs",
        ["knowledge_base_id"],
    )
    op.create_index("ix_shadow_agent_runs_status", "shadow_agent_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_shadow_agent_runs_status", table_name="shadow_agent_runs")
    op.drop_index("ix_shadow_agent_runs_knowledge_base_id", table_name="shadow_agent_runs")
    op.drop_index("ix_shadow_agent_runs_user_id", table_name="shadow_agent_runs")
    op.drop_table("shadow_agent_runs")


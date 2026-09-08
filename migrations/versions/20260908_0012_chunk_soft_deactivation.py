"""Add soft deactivation for knowledge chunks.

Revision ID: 20260908_0012
Revises: 20260906_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0012"
down_revision: str | None = "20260906_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "knowledge_chunks",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_index("ix_knowledge_chunks_is_active", "knowledge_chunks", ["is_active"])
    op.alter_column("knowledge_chunks", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_is_active", table_name="knowledge_chunks")
    op.drop_column("knowledge_chunks", "is_active")

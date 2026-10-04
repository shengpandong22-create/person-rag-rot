"""Add persistent chat retrieval expansion claims.

Revision ID: 20261004_0014
Revises: 20260908_0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261004_0014"
down_revision: str | None = "20260908_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_retrieval_expansions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "request_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "trace",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_message_id"], ["chat_messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["result_message_id"], ["chat_messages.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        sa.UniqueConstraint("parent_message_id"),
        sa.UniqueConstraint("result_message_id"),
    )
    op.create_index(
        "ix_chat_retrieval_expansions_idempotency_key",
        "chat_retrieval_expansions",
        ["idempotency_key"],
    )
    op.create_index(
        "ix_chat_retrieval_expansions_parent_message_id",
        "chat_retrieval_expansions",
        ["parent_message_id"],
    )
    op.create_index(
        "ix_chat_retrieval_expansions_status",
        "chat_retrieval_expansions",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chat_retrieval_expansions_status",
        table_name="chat_retrieval_expansions",
    )
    op.drop_index(
        "ix_chat_retrieval_expansions_parent_message_id",
        table_name="chat_retrieval_expansions",
    )
    op.drop_index(
        "ix_chat_retrieval_expansions_idempotency_key",
        table_name="chat_retrieval_expansions",
    )
    op.drop_table("chat_retrieval_expansions")

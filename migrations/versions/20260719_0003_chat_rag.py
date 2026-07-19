"""chat sessions and grounded citations

Revision ID: 20260719_0003
Revises: 20260719_0002
Create Date: 2026-07-19 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260719_0003"
down_revision: str | None = "20260719_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_sessions_knowledge_base_id", "chat_sessions", ["knowledge_base_id"])
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("retrieval_diagnostics", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_table(
        "chat_citations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["knowledge_chunks.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "chunk_id", name="uq_message_chunk_citation"),
    )
    op.create_index("ix_chat_citations_message_id", "chat_citations", ["message_id"])
    op.create_index("ix_chat_citations_chunk_id", "chat_citations", ["chunk_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_citations_chunk_id", table_name="chat_citations")
    op.drop_index("ix_chat_citations_message_id", table_name="chat_citations")
    op.drop_table("chat_citations")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_knowledge_base_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")

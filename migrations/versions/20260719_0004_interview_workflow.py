"""interview workflow sessions

Revision ID: 20260719_0004
Revises: 20260719_0003
Create Date: 2026-07-19 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260719_0004"
down_revision: str | None = "20260719_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(length=160), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_question_index", sa.Integer(), nullable=False),
        sa.Column("workflow_thread_id", sa.String(length=80), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_thread_id"),
    )
    op.create_index("ix_interview_sessions_user_id", "interview_sessions", ["user_id"])
    op.create_index(
        "ix_interview_sessions_knowledge_base_id",
        "interview_sessions",
        ["knowledge_base_id"],
    )
    op.create_index("ix_interview_sessions_status", "interview_sessions", ["status"])
    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=32), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("knowledge_points", JSONB(), nullable=False),
        sa.Column("reference_answer", sa.Text(), nullable=False),
        sa.Column("rubric", JSONB(), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("placeholder_feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "sequence", name="uq_interview_question_sequence"),
    )
    op.create_index("ix_interview_questions_session_id", "interview_questions", ["session_id"])
    op.create_table(
        "question_references",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["knowledge_chunks.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["interview_questions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "chunk_id", name="uq_question_chunk_reference"),
    )
    op.create_index("ix_question_references_question_id", "question_references", ["question_id"])
    op.create_table(
        "user_answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("answer_kind", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["interview_questions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "idempotency_key", name="uq_answer_idempotency"),
    )
    op.create_index("ix_user_answers_question_id", "user_answers", ["question_id"])
    op.create_table(
        "workflow_checkpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.String(length=80), nullable=False),
        sa.Column("node", sa.String(length=80), nullable=False),
        sa.Column("state", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_checkpoints_session_id", "workflow_checkpoints", ["session_id"])
    op.create_index("ix_workflow_checkpoints_thread_id", "workflow_checkpoints", ["thread_id"])


def downgrade() -> None:
    op.drop_index("ix_workflow_checkpoints_thread_id", table_name="workflow_checkpoints")
    op.drop_index("ix_workflow_checkpoints_session_id", table_name="workflow_checkpoints")
    op.drop_table("workflow_checkpoints")
    op.drop_index("ix_user_answers_question_id", table_name="user_answers")
    op.drop_table("user_answers")
    op.drop_index("ix_question_references_question_id", table_name="question_references")
    op.drop_table("question_references")
    op.drop_index("ix_interview_questions_session_id", table_name="interview_questions")
    op.drop_table("interview_questions")
    op.drop_index("ix_interview_sessions_status", table_name="interview_sessions")
    op.drop_index("ix_interview_sessions_knowledge_base_id", table_name="interview_sessions")
    op.drop_index("ix_interview_sessions_user_id", table_name="interview_sessions")
    op.drop_table("interview_sessions")

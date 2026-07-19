"""evaluations and interview reports

Revision ID: 20260719_0005
Revises: 20260719_0004
Create Date: 2026-07-19 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260719_0005"
down_revision: str | None = "20260719_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("answer_id", sa.Uuid(), nullable=False),
        sa.Column("correctness", sa.Integer(), nullable=False),
        sa.Column("completeness", sa.Integer(), nullable=False),
        sa.Column("reasoning", sa.Integer(), nullable=False),
        sa.Column("communication", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("covered_points", JSONB(), nullable=False),
        sa.Column("missing_points", JSONB(), nullable=False),
        sa.Column("incorrect_claims", JSONB(), nullable=False),
        sa.Column("answer_evidence", JSONB(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("follow_up_recommended", sa.Boolean(), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("reviewed", sa.Boolean(), nullable=False),
        sa.Column("review_reasons", JSONB(), nullable=False),
        sa.Column("review_decision", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["answer_id"], ["user_answers.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["interview_questions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("answer_id", name="uq_evaluation_answer"),
    )
    op.create_index("ix_evaluations_question_id", "evaluations", ["question_id"])
    op.create_index("ix_evaluations_answer_id", "evaluations", ["answer_id"])
    op.create_index("ix_evaluations_status", "evaluations", ["status"])
    op.create_table(
        "evaluation_references",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["knowledge_chunks.id"]),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_id", "chunk_id", name="uq_evaluation_chunk_reference"),
    )
    op.create_index(
        "ix_evaluation_references_evaluation_id", "evaluation_references", ["evaluation_id"]
    )
    op.create_table(
        "interview_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("max_score", sa.Integer(), nullable=False),
        sa.Column("dimension_summary", JSONB(), nullable=False),
        sa.Column("knowledge_point_summary", JSONB(), nullable=False),
        sa.Column("error_summary", JSONB(), nullable=False),
        sa.Column("low_confidence_items", JSONB(), nullable=False),
        sa.Column("disputed_items", JSONB(), nullable=False),
        sa.Column("next_steps", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )


def downgrade() -> None:
    op.drop_table("interview_reports")
    op.drop_index("ix_evaluation_references_evaluation_id", table_name="evaluation_references")
    op.drop_table("evaluation_references")
    op.drop_index("ix_evaluations_status", table_name="evaluations")
    op.drop_index("ix_evaluations_answer_id", table_name="evaluations")
    op.drop_index("ix_evaluations_question_id", table_name="evaluations")
    op.drop_table("evaluations")

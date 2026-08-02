"""Scope profile-derived data to a knowledge base.

Revision ID: 20260802_0009
Revises: 20260802_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260802_0009"
down_revision: str | None = "20260802_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_and_backfill(table_name: str, evaluation_column: str) -> None:
    op.add_column(
        table_name,
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        sa.text(
            f"""
            UPDATE {table_name} target
            SET knowledge_base_id = interview.knowledge_base_id
            FROM evaluations evaluation
            JOIN interview_questions question ON question.id = evaluation.question_id
            JOIN interview_sessions interview ON interview.id = question.session_id
            WHERE target.{evaluation_column} = evaluation.id
            """
        )
    )
    op.alter_column(table_name, "knowledge_base_id", nullable=False)
    op.create_foreign_key(
        f"fk_{table_name}_knowledge_base",
        table_name,
        "knowledge_bases",
        ["knowledge_base_id"],
        ["id"],
    )
    op.create_index(
        f"ix_{table_name}_knowledge_base_id",
        table_name,
        ["knowledge_base_id"],
    )


def upgrade() -> None:
    _add_and_backfill("ability_profiles", "last_evaluation_id")
    _add_and_backfill("error_patterns", "last_evaluation_id")
    _add_and_backfill("review_tasks", "source_evaluation_id")
    _add_and_backfill("profile_update_events", "evaluation_id")

    op.drop_constraint("uq_ability_user_point", "ability_profiles", type_="unique")
    op.create_unique_constraint(
        "uq_ability_user_base_point",
        "ability_profiles",
        ["user_id", "knowledge_base_id", "knowledge_point"],
    )
    op.drop_constraint("uq_error_user_point_type", "error_patterns", type_="unique")
    op.create_unique_constraint(
        "uq_error_user_base_point_type",
        "error_patterns",
        ["user_id", "knowledge_base_id", "knowledge_point", "error_type"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_error_user_base_point_type", "error_patterns", type_="unique")
    op.create_unique_constraint(
        "uq_error_user_point_type",
        "error_patterns",
        ["user_id", "knowledge_point", "error_type"],
    )
    op.drop_constraint("uq_ability_user_base_point", "ability_profiles", type_="unique")
    op.create_unique_constraint(
        "uq_ability_user_point",
        "ability_profiles",
        ["user_id", "knowledge_point"],
    )
    for table_name in (
        "profile_update_events",
        "review_tasks",
        "error_patterns",
        "ability_profiles",
    ):
        op.drop_index(f"ix_{table_name}_knowledge_base_id", table_name=table_name)
        op.drop_constraint(f"fk_{table_name}_knowledge_base", table_name, type_="foreignkey")
        op.drop_column(table_name, "knowledge_base_id")

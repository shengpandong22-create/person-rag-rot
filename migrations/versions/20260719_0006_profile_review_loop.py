"""ability profile and review loop

Revision ID: 20260719_0006
Revises: 20260719_0005
Create Date: 2026-07-19 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260719_0006"
down_revision: str | None = "20260719_0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ability_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_point", sa.String(length=160), nullable=False),
        sa.Column("mastery_score", sa.Float(), nullable=False),
        sa.Column("confidence_weighted_count", sa.Float(), nullable=False),
        sa.Column("last_evaluation_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["last_evaluation_id"], ["evaluations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "knowledge_point", name="uq_ability_user_point"),
    )
    op.create_index("ix_ability_profiles_user_id", "ability_profiles", ["user_id"])

    op.create_table(
        "error_patterns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_point", sa.String(length=160), nullable=False),
        sa.Column("error_type", sa.String(length=64), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_evaluation_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["last_evaluation_id"], ["evaluations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "knowledge_point", "error_type", name="uq_error_user_point_type"
        ),
    )
    op.create_index("ix_error_patterns_user_id", "error_patterns", ["user_id"])

    op.create_table(
        "review_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_point", sa.String(length=160), nullable=False),
        sa.Column("error_type", sa.String(length=64), nullable=False),
        sa.Column("source_evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_evaluation_id"], ["evaluations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_tasks_user_id", "review_tasks", ["user_id"])
    op.create_index("ix_review_tasks_status", "review_tasks", ["status"])

    op.create_table(
        "profile_update_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=80), nullable=False),
        sa.Column("applied", sa.Boolean(), nullable=False),
        sa.Column("changes", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_id", name="uq_profile_event_evaluation"),
    )
    op.create_index("ix_profile_update_events_user_id", "profile_update_events", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_profile_update_events_user_id", table_name="profile_update_events")
    op.drop_table("profile_update_events")
    op.drop_index("ix_review_tasks_status", table_name="review_tasks")
    op.drop_index("ix_review_tasks_user_id", table_name="review_tasks")
    op.drop_table("review_tasks")
    op.drop_index("ix_error_patterns_user_id", table_name="error_patterns")
    op.drop_table("error_patterns")
    op.drop_index("ix_ability_profiles_user_id", table_name="ability_profiles")
    op.drop_table("ability_profiles")

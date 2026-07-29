"""Add two-layer ability profile metadata and review verification streak.

Revision ID: 20260729_0007
Revises: 20260719_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260729_0007"
down_revision: str | None = "20260719_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table_name in ("ability_profiles", "error_patterns", "review_tasks"):
        op.add_column(
            table_name,
            sa.Column(
                "profile_level",
                sa.String(length=20),
                nullable=False,
                server_default="legacy",
            ),
        )
        op.add_column(table_name, sa.Column("topic_key", sa.String(length=80), nullable=True))
        op.add_column(table_name, sa.Column("topic_title", sa.String(length=120), nullable=True))
        op.add_column(table_name, sa.Column("subtopic_key", sa.String(length=80), nullable=True))
        op.add_column(table_name, sa.Column("subtopic_title", sa.String(length=120), nullable=True))
    op.add_column(
        "review_tasks",
        sa.Column("verification_streak", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_ability_user_topic", "ability_profiles", ["user_id", "topic_key"])
    op.create_index("ix_review_user_topic", "review_tasks", ["user_id", "topic_key", "status"])


def downgrade() -> None:
    op.drop_index("ix_review_user_topic", table_name="review_tasks")
    op.drop_index("ix_ability_user_topic", table_name="ability_profiles")
    op.drop_column("review_tasks", "verification_streak")
    for table_name in ("review_tasks", "error_patterns", "ability_profiles"):
        op.drop_column(table_name, "subtopic_title")
        op.drop_column(table_name, "subtopic_key")
        op.drop_column(table_name, "topic_title")
        op.drop_column(table_name, "topic_key")
        op.drop_column(table_name, "profile_level")

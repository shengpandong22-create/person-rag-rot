"""Persist stable profile routing on interview sessions.

Revision ID: 20260802_0008
Revises: 20260729_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0008"
down_revision: str | None = "20260729_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("interview_sessions", sa.Column("profile_topic_key", sa.String(80)))
    op.add_column("interview_sessions", sa.Column("profile_topic_title", sa.String(120)))
    op.add_column("interview_sessions", sa.Column("profile_subtopic_key", sa.String(80)))
    op.add_column("interview_sessions", sa.Column("profile_subtopic_title", sa.String(120)))


def downgrade() -> None:
    op.drop_column("interview_sessions", "profile_subtopic_title")
    op.drop_column("interview_sessions", "profile_subtopic_key")
    op.drop_column("interview_sessions", "profile_topic_title")
    op.drop_column("interview_sessions", "profile_topic_key")

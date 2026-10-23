"""Persist a user-selected coverage target for an interview.

Revision ID: 20261022_0016
Revises: 20261005_0015
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261022_0016"
down_revision = "20261005_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("coverage_catalog_point_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_interview_sessions_coverage_catalog_point",
        "interview_sessions",
        "knowledge_catalog_points",
        ["coverage_catalog_point_id"],
        ["id"],
    )
    op.create_index(
        "ix_interview_sessions_coverage_catalog_point_id",
        "interview_sessions",
        ["coverage_catalog_point_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_interview_sessions_coverage_catalog_point_id", "interview_sessions")
    op.drop_constraint(
        "fk_interview_sessions_coverage_catalog_point", "interview_sessions", type_="foreignkey"
    )
    op.drop_column("interview_sessions", "coverage_catalog_point_id")

"""Isolate controlled practice interviews from profile training.

Revision ID: 20261023_0017
Revises: 20261022_0016
"""

import sqlalchemy as sa
from alembic import op

revision = "20261023_0017"
down_revision = "20261022_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column(
            "training_mode",
            sa.String(32),
            nullable=False,
            server_default="profile_training",
        ),
    )


def downgrade() -> None:
    op.drop_column("interview_sessions", "training_mode")

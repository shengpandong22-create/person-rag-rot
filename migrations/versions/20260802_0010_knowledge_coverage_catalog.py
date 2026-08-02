"""Add knowledge coverage catalog.

Revision ID: 20260802_0010
Revises: 20260802_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260802_0010"
down_revision: str | None = "20260802_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_catalog_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("point_key", sa.String(160), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("knowledge_base_id", "point_key", name="uq_catalog_base_point"),
    )
    op.create_index(
        "ix_knowledge_catalog_points_knowledge_base_id",
        "knowledge_catalog_points",
        ["knowledge_base_id"],
    )
    op.create_table(
        "knowledge_catalog_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_point_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_point_id"], ["knowledge_catalog_points.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["knowledge_chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("knowledge_point_id", "chunk_id", name="uq_catalog_point_chunk"),
    )
    op.create_index(
        "ix_knowledge_catalog_sources_knowledge_point_id",
        "knowledge_catalog_sources",
        ["knowledge_point_id"],
    )
    op.create_index(
        "ix_knowledge_catalog_sources_document_id", "knowledge_catalog_sources", ["document_id"]
    )
    op.create_index(
        "ix_knowledge_catalog_sources_chunk_id", "knowledge_catalog_sources", ["chunk_id"]
    )
    op.create_table(
        "question_coverage_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_point_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["question_id"], ["interview_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["knowledge_point_id"], ["knowledge_catalog_points.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "knowledge_point_id", name="uq_question_coverage_point"),
    )
    op.create_index(
        "ix_question_coverage_points_question_id", "question_coverage_points", ["question_id"]
    )
    op.create_index(
        "ix_question_coverage_points_knowledge_point_id",
        "question_coverage_points",
        ["knowledge_point_id"],
    )


def downgrade() -> None:
    op.drop_table("question_coverage_points")
    op.drop_table("knowledge_catalog_sources")
    op.drop_table("knowledge_catalog_points")

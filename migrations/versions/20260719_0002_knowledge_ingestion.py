"""knowledge ingestion foundation

Revision ID: 20260719_0002
Revises: 20260718_0001
Create Date: 2026-07-19 00:00:00
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260719_0002"
down_revision: str | None = "20260718_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.bulk_insert(
        sa.table(
            "users",
            sa.column("id", sa.Uuid()),
            sa.column("email", sa.String()),
            sa.column("display_name", sa.String()),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "id": DEFAULT_USER_ID,
                "email": "local@agentmentor.dev",
                "display_name": "Local User",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        ],
    )
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_bases_user_id", "knowledge_bases", ["user_id"])
    op.create_table(
        "source_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("logical_name", sa.String(length=300), nullable=False),
        sa.Column("original_filename", sa.String(length=300), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=200), nullable=True),
        sa.Column("trust_level", sa.String(length=32), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("knowledge_base_id", "content_hash", name="uq_document_content_hash"),
        sa.UniqueConstraint(
            "knowledge_base_id", "logical_name", "version", name="uq_document_version"
        ),
    )
    op.create_index(
        "ix_source_documents_knowledge_base_id", "source_documents", ["knowledge_base_id"]
    )
    op.create_index("ix_source_documents_status", "source_documents", ["status"])
    op.create_index("ix_source_documents_is_active", "source_documents", ["is_active"])
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("heading_path", sa.JSON(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_chunk_document_index"),
    )
    op.execute(
        "ALTER TABLE knowledge_chunks "
        "ALTER COLUMN search_text TYPE tsvector "
        "USING to_tsvector('simple', search_text)"
    )
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.execute("CREATE INDEX ix_chunks_search_text ON knowledge_chunks USING gin (search_text)")
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.create_table(
        "knowledge_points",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["knowledge_points.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )


def downgrade() -> None:
    op.drop_table("knowledge_points")
    op.drop_index("ix_chunks_embedding_hnsw", table_name="knowledge_chunks")
    op.drop_index("ix_chunks_search_text", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_table("source_documents")
    op.drop_table("knowledge_bases")
    op.execute(f"DELETE FROM users WHERE id = '{DEFAULT_USER_ID}'")

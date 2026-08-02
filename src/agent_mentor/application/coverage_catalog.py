from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_mentor.infrastructure.database.models import (
    KnowledgeCatalogPointModel,
    KnowledgeCatalogSourceModel,
    KnowledgeChunkModel,
    QuestionCoverageModel,
)

_GENERIC_HEADINGS = {
    "概述",
    "简介",
    "总结",
    "前言",
    "背景",
    "参考资料",
    "核心知识点",
    "面试题",
    "学习资料",
}


def catalog_title(heading_path: list[str], content: str) -> str | None:
    """Choose a deterministic point title without asking the LLM to invent identifiers."""
    for heading in reversed(heading_path):
        title = re.sub(r"^(知识点|主题)\s*[：:]\s*", "", heading).strip()
        if 2 <= len(title) <= 120 and title not in _GENERIC_HEADINGS:
            return title
    first_line = content.strip().splitlines()[0].lstrip("# ").strip() if content.strip() else ""
    if 2 <= len(first_line) <= 80 and first_line not in _GENERIC_HEADINGS:
        return first_line
    return None


def catalog_point_key(title: str) -> str:
    normalized = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", title.casefold())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


async def sync_document_catalog(
    db: AsyncSession,
    *,
    knowledge_base_id: UUID,
    document_id: UUID,
) -> int:
    """Replace one document's source links while preserving stable KB-level points."""
    await db.execute(
        delete(KnowledgeCatalogSourceModel).where(
            KnowledgeCatalogSourceModel.document_id == document_id
        )
    )
    chunks = list(
        (
            await db.scalars(
                select(KnowledgeChunkModel)
                .where(KnowledgeChunkModel.document_id == document_id)
                .order_by(KnowledgeChunkModel.chunk_index)
            )
        ).all()
    )
    has_nested_headings = any(len(chunk.heading_path) > 1 for chunk in chunks)
    linked = 0
    for chunk in chunks:
        if has_nested_headings and len(chunk.heading_path) <= 1:
            continue
        title = catalog_title(chunk.heading_path, chunk.content)
        if title is None:
            continue
        key = catalog_point_key(title)
        point = await db.scalar(
            select(KnowledgeCatalogPointModel).where(
                KnowledgeCatalogPointModel.knowledge_base_id == knowledge_base_id,
                KnowledgeCatalogPointModel.point_key == key,
            )
        )
        if point is None:
            point = KnowledgeCatalogPointModel(
                id=uuid4(),
                knowledge_base_id=knowledge_base_id,
                point_key=key,
                title=title,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(point)
            await db.flush()
        db.add(
            KnowledgeCatalogSourceModel(
                id=uuid4(),
                knowledge_point_id=point.id,
                document_id=document_id,
                chunk_id=chunk.id,
                created_at=datetime.now(UTC),
            )
        )
        linked += 1
    await db.flush()
    return linked


async def map_question_coverage(
    db: AsyncSession, *, question_id: UUID, chunk_ids: list[UUID]
) -> int:
    if not chunk_ids:
        return 0
    point_ids = set(
        (
            await db.scalars(
                select(KnowledgeCatalogSourceModel.knowledge_point_id).where(
                    KnowledgeCatalogSourceModel.chunk_id.in_(tuple(chunk_ids))
                )
            )
        ).all()
    )
    for point_id in point_ids:
        db.add(
            QuestionCoverageModel(
                id=uuid4(),
                question_id=question_id,
                knowledge_point_id=point_id,
                created_at=datetime.now(UTC),
            )
        )
    return len(point_ids)

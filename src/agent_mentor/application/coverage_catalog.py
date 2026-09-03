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
    "小结",
    "前言",
    "背景",
    "结论",
    "参考资料",
    "核心知识点",
    "面试题",
    "学习资料",
    "它的价值",
    "它的限制",
    "边界",
    "关键规则",
    "核心结论",
    "为什么这么做",
    "面试策略",
    "面试必须准确描述",
    "面试要能讲清的三点",
    "教案正文",
    "学员疑问与讨论记录",
    "本课结论",
    "本课自测",
    "最终自测清单",
    "自测结果",
    "先说结论",
    "核心链路图",
    "状态流全景",
    "评分数据流全景",
    "最小源码定位表",
}

_NON_KNOWLEDGE_HEADINGS = {
    "教案正文",
    "学员疑问与讨论记录",
    "本课结论",
    "本课自测",
    "最终自测清单",
    "自测结果",
    "先说结论",
    "核心链路图",
    "状态流全景",
    "评分数据流全景",
    "最小源码定位表",
}


def catalog_title(heading_path: list[str], content: str) -> str | None:
    """Choose a deterministic point title without asking the LLM to invent identifiers."""
    if heading_path and _is_non_knowledge_title(_clean_catalog_title(heading_path[-1])):
        return None
    for heading in reversed(heading_path):
        title = _clean_catalog_title(heading)
        if _is_specific_catalog_title(title, max_length=120):
            return title
    if _is_non_knowledge_path(heading_path):
        return None
    first_line = content.strip().splitlines()[0].lstrip("# ").strip() if content.strip() else ""
    first_line = _clean_catalog_title(first_line)
    if _is_specific_catalog_title(first_line, max_length=80):
        return first_line
    return None


def _clean_catalog_title(title: str) -> str:
    title = re.sub(r"^(知识点|主题)\s*[：:]\s*", "", title).strip()
    title = re.sub(r"^\s*(第\s*)?[一二三四五六七八九十\d]+\s*[章节课]\s*[：:、.-]*\s*", "", title)
    title = re.sub(r"^\s*\d+(?:\.\d+)*\s*[：:、.-]*\s*", "", title)
    title = re.sub(r"^\s*[一二三四五六七八九十\d]+\s*[、.．]\s*", "", title)
    title = re.sub(r"^\s*[（(]?[一二三四五六七八九十\d]+[）)]\s*", "", title)
    return title.strip()


def _is_specific_catalog_title(title: str, *, max_length: int) -> bool:
    if not (2 <= len(title) <= max_length):
        return False
    normalized = re.sub(r"\s+", "", title)
    if normalized in _GENERIC_HEADINGS:
        return False
    return not _is_non_knowledge_title(normalized)


_GENERIC_HEADING_PATTERNS = (
    re.compile(r"^Q\d*[：:]?"),
    re.compile(r"^面试.*(重点|策略|表达|必背|清单)$"),
    re.compile(r".*自测.*"),
    re.compile(r".*源码定位.*"),
    re.compile(r".*(链路图|流程图|全景图)$"),
)


def _is_non_knowledge_path(heading_path: list[str]) -> bool:
    normalized_path = [_clean_catalog_title(heading) for heading in heading_path]
    return any(_is_non_knowledge_title(title) for title in normalized_path)


def _is_non_knowledge_title(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title)
    if normalized in _NON_KNOWLEDGE_HEADINGS:
        return True
    return any(pattern.search(normalized) for pattern in _GENERIC_HEADING_PATTERNS)


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

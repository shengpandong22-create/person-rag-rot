"""检索工具模块 — 查询归一化、RRF 融合、引用验证、证据上下文渲染。

核心流程：
    normalize_query → 向量检索 + 全文检索 → reciprocal_rank_fusion → 排序取 top_k
    → validate_citations（引用合法性校验）
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from agent_mentor.ports.knowledge_retriever import RetrievedChunk


def normalize_query(query: str) -> str:
    """查询归一化：合并多余空白，保留 Java 类名、缩写和异常名。
    
    例："HashMap  的   扩容机制？" → "HashMap 的 扩容机制？"
    """
    return re.sub(r"\s+", " ", query).strip()


def reciprocal_rank_fusion(ranked_lists: list[list[UUID]], *, rrf_k: int = 60) -> dict[UUID, float]:
    """RRF（Reciprocal Rank Fusion）融合多路检索排名。
    
    原理：对每个 chunk，其在各路检索中的排名越靠前，得分越高。
    公式：score = Σ 1/(k + rank)，k=60 是经验常数。
    
    例：某 chunk 在向量检索排第1、全文检索排第5
        score = 1/(60+1) + 1/(60+5) ≈ 0.0164 + 0.0154 = 0.0318
    
    Args:
        ranked_lists: 多路检索的排名列表，每个元素是 chunk_id 列表（按排名升序）
        rrf_k: RRF 平滑常数，默认 60
    Returns:
        {chunk_id: 融合分数}，分数越高越相关
    """
    scores: dict[UUID, float] = {}
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
    return scores


def validate_citations(citation_ids: list[UUID], context: list[RetrievedChunk]) -> None:
    """验证 LLM 返回的引用 chunk_id 是否在检索上下文中（防止 LLM 编造引用）。
    
    Raises:
        ValueError: 如果存在不在 context 中的 chunk_id
    """
    allowed = {chunk.chunk_id for chunk in context}
    invalid = [chunk_id for chunk_id in citation_ids if chunk_id not in allowed]
    if invalid:
        joined = ", ".join(str(chunk_id) for chunk_id in invalid)
        raise ValueError(f"Citations are not in the current retrieval context: {joined}")


@dataclass(frozen=True, slots=True)
class EvidenceContext:
    """证据上下文 — 将检索到的 chunks 渲染为 LLM prompt 中的资料块。
    
    渲染格式示例：
        [1] chunk_id=xxx-xxx
        title=Spring面试.md
        location=第二章 > 2.1 Bean生命周期
        trust_level=curated
        content=Bean的生命周期包括...
    """
    chunks: tuple[RetrievedChunk, ...]

    def render_for_prompt(self) -> str:
        """将 chunks 渲染为 prompt 中的资料引用格式"""
        blocks: list[str] = []
        for index, chunk in enumerate(self.chunks, start=1):
            location = " > ".join(chunk.heading_path)
            if chunk.page_number is not None:
                location = (
                    f"{location} p.{chunk.page_number}" if location else f"p.{chunk.page_number}"
                )
            blocks.append(
                "\n".join(
                    [
                        f"[{index}] chunk_id={chunk.chunk_id}",
                        f"title={chunk.document_title}",
                        f"location={location or 'unknown'}",
                        f"trust_level={chunk.trust_level}",
                        f"content={chunk.content}",
                    ]
                )
            )
        return "\n\n".join(blocks)

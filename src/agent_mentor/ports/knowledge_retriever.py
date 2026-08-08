"""知识检索端口 — 定义检索系统的输入/输出契约，业务层只依赖此接口，不感知底层实现。

数据流向：
    RetrievalQuery（输入）→ KnowledgeRetriever.retrieve() → list[RetrievedChunk]（输出）
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from agent_mentor.domain.knowledge import TrustLevel


class RetrievalMode(StrEnum):
    """检索模式：VECTOR=仅向量检索, HYBRID=向量+全文混合检索（默认）"""
    VECTOR = "vector"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """检索请求参数。
    
    top_k=6:     最终返回的 chunk 数量
    candidate_k=20: 向量和全文各召回候选数，两路共最多 40 个候选，RRF 融合后取前 top_k
    mode:        默认 HYBRID，同时走向量和全文两路
    trust_levels: 可选，按资料可信等级过滤（OFFICIAL/CURATED/COMMUNITY/UNKNOWN）
    """
    knowledge_base_id: UUID
    query: str
    top_k: int = 6
    candidate_k: int = 20
    mode: RetrievalMode = RetrievalMode.HYBRID
    trust_levels: tuple[TrustLevel, ...] | None = None


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """单个检索结果 — 包含 chunk 内容、来源、排名、分数等完整信息。
    
    score:           RRF 融合后的最终分数（用于排序）
    vector_rank:     向量检索中的排名（None 表示未从向量路召回）
    text_rank:       全文检索中的排名（None 表示未从全文路召回）
    retrieval_explanation: 可读的检索解释，如 "RRF=0.0328 | vector_rank=1 | text_rank=3"
    """
    chunk_id: UUID
    document_id: UUID
    document_title: str
    source_url: str | None
    trust_level: str
    heading_path: tuple[str, ...]  # 文档标题层级路径，如 ("第二章", "2.1 概述")
    page_number: int | None
    block_type: str  # paragraph/code/table/list
    chunk_index: int  # 在文档内的分块序号
    content: str
    score: float
    retrieval_explanation: str
    vector_rank: int | None = None
    text_rank: int | None = None
    vector_score: float | None = None
    text_score: float | None = None


class KnowledgeRetriever(Protocol):
    """知识检索器接口（Protocol 协议类，无需继承，鸭子类型）。
    
    实现类：PostgresHybridRetriever（生产）、FakeKnowledgeRetriever（测试）
    """
    async def retrieve(self, query: RetrievalQuery) -> list[RetrievedChunk]: ...

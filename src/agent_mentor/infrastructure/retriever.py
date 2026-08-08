"""PostgreSQL 混合检索器 — 向量检索 + 全文检索 + RRF 融合。

这是项目检索系统的核心实现，完整流程：

    用户查询
      → normalize_query() 归一化
      → _vector_candidates()：pgvector cosine_distance 向量检索
      → _text_candidates()：PostgreSQL websearch_to_tsquery 全文检索
      → reciprocal_rank_fusion()：RRF 融合两路排名
      → 后处理：去重 + 文档去重（max_chunks_per_document） + 去相邻 chunk
      → 截取 top_k 返回

关键技术：
    - 向量索引：HNSW（pgvector hnsw index）
    - 全文索引：GIN on tsvector
    - 融合算法：Reciprocal Rank Fusion（k=60）
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.domain.knowledge import DocumentStatus
from agent_mentor.infrastructure.database.models import KnowledgeChunkModel, SourceDocumentModel
from agent_mentor.ports.embedding_gateway import EmbeddingGateway
from agent_mentor.ports.knowledge_retriever import (
    RetrievalMode,
    RetrievalQuery,
    RetrievedChunk,
)
from agent_mentor.rag.retrieval import normalize_query, reciprocal_rank_fusion


@dataclass(frozen=True, slots=True)
class _Candidate:
    """内部候选结构 — 关联 chunk 和 document，携带排名和分数"""
    chunk: KnowledgeChunkModel
    document: SourceDocumentModel
    rank: int      # 在该路检索中的排名（1-based）
    score: float   # 该路检索的原始分数（向量=1-距离, 全文=ts_rank）


class PostgresHybridRetriever:
    """PostgreSQL 混合检索器 — 生产环境的核心检索实现。
    
    依赖：
        - pgvector 扩展（向量检索）
        - PostgreSQL 全文检索（tsvector + tsquery）
        - EmbeddingGateway（文本→向量）
    """

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        embedding: EmbeddingGateway,
        *,
        max_chunks_per_document: int,  # 每篇文档最多返回的 chunk 数，避免单一文档霸榜
    ) -> None:
        self._sessions = sessions
        self._embedding = embedding
        self._max_chunks_per_document = max_chunks_per_document

    async def retrieve(self, query: RetrievalQuery) -> list[RetrievedChunk]:
        """执行混合检索，返回 top_k 个去重后的 RetrievedChunk。
        
        步骤：
            1. 查询归一化
            2. 向量检索（pgvector cosine_distance）
            3. 全文检索（PostgreSQL websearch_to_tsquery）— 仅 HYBRID 模式
            4. RRF 融合两路排名
            5. 后处理：文档去重 + 去相邻 chunk
            6. 截取 top_k
        """
        normalized = normalize_query(query.query)
        if not normalized:
            return []

        # 并行执行向量和全文检索（注意：这里实际上是串行的，优化空间）
        async with self._sessions() as session:
            vector_candidates = await self._vector_candidates(session, query, normalized)
            text_candidates: list[_Candidate] = []
            if query.mode is RetrievalMode.HYBRID:
                text_candidates = await self._text_candidates(session, query, normalized)

        # 构建 chunk_id → candidate 映射（去重：同一 chunk 可能同时在两路出现）
        by_id = {
            candidate.chunk.id: candidate for candidate in [*vector_candidates, *text_candidates]
        }
        # 提取各路排名和分数
        vector_ranks = {candidate.chunk.id: candidate.rank for candidate in vector_candidates}
        text_ranks = {candidate.chunk.id: candidate.rank for candidate in text_candidates}
        vector_scores = {candidate.chunk.id: candidate.score for candidate in vector_candidates}
        text_scores = {candidate.chunk.id: candidate.score for candidate in text_candidates}

        # RRF 融合：综合两路排名计算最终分数
        fused = reciprocal_rank_fusion([list(vector_ranks), list(text_ranks)])
        ordered_ids = sorted(fused, key=lambda chunk_id: fused[chunk_id], reverse=True)

        # 后处理：按 RRF 分数降序遍历，去重 + 截断
        results: list[RetrievedChunk] = []
        per_document: dict[UUID, int] = {}  # 每篇文档已选 chunk 计数
        seen_neighbors: set[tuple[UUID, int]] = set()  # 已选 chunk 的相邻标记
        for chunk_id in ordered_ids:
            candidate = by_id[chunk_id]
            document_id = candidate.document.id

            # 每篇文档最多 max_chunks_per_document 个 chunk
            if per_document.get(document_id, 0) >= self._max_chunks_per_document:
                continue

            # 跳过相邻 chunk：避免返回内容高度重叠的连续分块
            neighbor_key = (document_id, candidate.chunk.chunk_index)
            if (document_id, candidate.chunk.chunk_index - 1) in seen_neighbors:
                continue
            seen_neighbors.add(neighbor_key)
            per_document[document_id] = per_document.get(document_id, 0) + 1

            results.append(
                RetrievedChunk(
                    chunk_id=candidate.chunk.id,
                    document_id=document_id,
                    document_title=candidate.document.title,
                    source_url=candidate.document.source_url,
                    trust_level=str(candidate.document.trust_level),
                    heading_path=tuple(candidate.chunk.heading_path),
                    page_number=candidate.chunk.page_number,
                    block_type=_infer_retrieved_block_type(candidate.chunk.content),
                    chunk_index=candidate.chunk.chunk_index,
                    content=candidate.chunk.content,
                    score=fused[chunk_id],
                    retrieval_explanation=_retrieval_explanation(
                        fused_score=fused[chunk_id],
                        vector_rank=vector_ranks.get(chunk_id),
                        text_rank=text_ranks.get(chunk_id),
                        vector_score=vector_scores.get(chunk_id),
                        text_score=text_scores.get(chunk_id),
                    ),
                    vector_rank=vector_ranks.get(chunk_id),
                    text_rank=text_ranks.get(chunk_id),
                    vector_score=vector_scores.get(chunk_id),
                    text_score=text_scores.get(chunk_id),
                )
            )
            if len(results) >= query.top_k:
                break
        return results

    def _base_query(
        self, query: RetrievalQuery
    ) -> Select[tuple[KnowledgeChunkModel, SourceDocumentModel]]:
        """构建基础查询：JOIN chunks 和 documents，过滤知识库 + READY 状态 + 活跃 + 信任等级"""
        statement = (
            select(KnowledgeChunkModel, SourceDocumentModel)
            .join(SourceDocumentModel, SourceDocumentModel.id == KnowledgeChunkModel.document_id)
            .where(
                SourceDocumentModel.knowledge_base_id == query.knowledge_base_id,
                SourceDocumentModel.status == DocumentStatus.READY,
                SourceDocumentModel.is_active.is_(True),
            )
        )
        if query.trust_levels:
            statement = statement.where(
                SourceDocumentModel.trust_level.in_(tuple(query.trust_levels))
            )
        return statement

    async def _vector_candidates(
        self, session: AsyncSession, query: RetrievalQuery, normalized: str
    ) -> list[_Candidate]:
        """向量检索：将查询文本转为向量，用 pgvector cosine_distance 排序，取前 candidate_k 个。
        
        score = 1 - cosine_distance（距离越小越相关，转换为分数越高越相关）
        """
        vector = await self._embedding.embed_query(normalized)
        distance = KnowledgeChunkModel.embedding.cosine_distance(vector).label("distance")
        rows = (
            await session.execute(
                self._base_query(query)
                .add_columns(distance)
                .order_by(distance)
                .limit(query.candidate_k)
            )
        ).all()
        return [
            _Candidate(chunk=chunk, document=document, rank=rank, score=1.0 - float(distance_value))
            for rank, (chunk, document, distance_value) in enumerate(rows, start=1)
        ]

    async def _text_candidates(
        self, session: AsyncSession, query: RetrievalQuery, normalized: str
    ) -> list[_Candidate]:
        """全文检索：使用 PostgreSQL websearch_to_tsquery 解析查询。

        排序使用 ts_rank_cd，最终取前 candidate_k 个。
        
        websearch_to_tsquery：将用户查询转为 PostgreSQL 全文搜索语法
        ts_rank_cd：基于覆盖密度的排名函数
        coalesce：优先用预计算的 search_text 列，回退到运行时生成 tsvector
        """
        ts_query = func.websearch_to_tsquery("simple", normalized)
        rank_expr = func.ts_rank_cd(
            func.coalesce(
                KnowledgeChunkModel.search_text,
                func.to_tsvector("simple", KnowledgeChunkModel.content),
            ),
            ts_query,
        ).label("text_rank")
        rows = (
            await session.execute(
                self._base_query(query)
                .add_columns(rank_expr)
                .where(
                    func.coalesce(
                        KnowledgeChunkModel.search_text,
                        func.to_tsvector("simple", KnowledgeChunkModel.content),
                    ).op("@@")(ts_query)  # @@ 是 PostgreSQL 全文匹配操作符
                )
                .order_by(rank_expr.desc())
                .limit(query.candidate_k)
            )
        ).all()
        return [
            _Candidate(chunk=chunk, document=document, rank=rank, score=float(score))
            for rank, (chunk, document, score) in enumerate(rows, start=1)
        ]


def _infer_retrieved_block_type(content: str) -> str:
    """推断检索结果的块类型：code/table/list/paragraph"""
    stripped = content.strip()
    if not stripped:
        return "unknown"
    if stripped.startswith("```") or stripped.endswith("```"):
        return "code"
    if stripped.count("|") >= 4:
        return "table"
    if stripped.startswith(("- ", "* ", "+ ")):
        return "list"
    return "paragraph"


def _retrieval_explanation(
    *,
    fused_score: float,
    vector_rank: int | None,
    text_rank: int | None,
    vector_score: float | None,
    text_score: float | None,
) -> str:
    """生成检索结果的可读解释字符串。
    
    格式示例："RRF=0.0328 | vector_rank=1 | text_rank=3 | vector_score=0.8560 | text_score=0.4320"
    """
    signals: list[str] = [f"RRF={fused_score:.4f}"]
    if vector_rank is not None:
        signals.append(f"vector_rank={vector_rank}")
    if text_rank is not None:
        signals.append(f"text_rank={text_rank}")
    if vector_score is not None:
        signals.append(f"vector_score={vector_score:.4f}")
    if text_score is not None:
        signals.append(f"text_score={text_score:.4f}")
    return " | ".join(signals)

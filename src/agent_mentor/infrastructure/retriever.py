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

import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Select, String, case, cast, func, literal, or_, select
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
    rank: int  # 在该路检索中的排名（1-based）
    score: float  # 该路检索的原始分数（向量=1-距离, 全文=ts_rank）


class RetrievalExperimentMode(StrEnum):
    """Eval-only ranking variants; the default exactly matches production."""

    VECTOR_ONLY = "vector-only"
    TEXT_ONLY = "text-only"
    RRF = "rrf"
    RRF_HEURISTIC = "rrf-heuristic"


class RetrievalFilterReason(StrEnum):
    PER_DOCUMENT_LIMIT = "per_document_limit"
    ADJACENT_CHUNK = "adjacent_chunk"
    TOP_K_CUTOFF = "top_k_cutoff"


class AdjacentFilterStrategy(StrEnum):
    """Eval-only adjacent-block variants; CURRENT preserves production behavior."""

    CURRENT = "current"
    SAME_HEADING = "same-heading"


class CandidateExpansionStrategy(StrEnum):
    """Eval-only candidate sources; production remains vector/text as configured."""

    NONE = "none"
    HEADING_LEXICAL = "heading-lexical"
    HEADING_SHADOW = "heading-shadow"


@dataclass(frozen=True, slots=True)
class FilteredRetrievalCandidate:
    chunk: RetrievedChunk
    reason: RetrievalFilterReason


@dataclass(frozen=True, slots=True)
class RetrievalDiagnostics:
    """Eval-only view of each stage of the unchanged retrieval pipeline."""

    vector_candidates: tuple[RetrievedChunk, ...]
    heading_candidates: tuple[RetrievedChunk, ...]
    text_candidates: tuple[RetrievedChunk, ...]
    ordered_candidates: tuple[RetrievedChunk, ...]
    post_filter_candidates: tuple[RetrievedChunk, ...]
    filtered_out: tuple[FilteredRetrievalCandidate, ...]
    final_results: tuple[RetrievedChunk, ...]
    supplemental_candidates: tuple[RetrievedChunk, ...] = ()


def _merge_query_variant_candidates(
    ranked_variants: list[list[_Candidate]], *, candidate_k: int
) -> list[_Candidate]:
    """RRF-merge eval-only query views into one fixed-size vector candidate list."""
    if len(ranked_variants) <= 1:
        return ranked_variants[0] if ranked_variants else []
    by_id = {candidate.chunk.id: candidate for ranked in ranked_variants for candidate in ranked}
    fused = reciprocal_rank_fusion(
        [[candidate.chunk.id for candidate in ranked] for ranked in ranked_variants]
    )
    ordered_ids = sorted(fused, key=fused.__getitem__, reverse=True)[:candidate_k]
    return [
        _Candidate(
            chunk=by_id[chunk_id].chunk,
            document=by_id[chunk_id].document,
            rank=rank,
            score=fused[chunk_id],
        )
        for rank, chunk_id in enumerate(ordered_ids, start=1)
    ]


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
        max_chunks_per_document: int | None,  # None 仅供 eval 关闭单文档限额
    ) -> None:
        self._sessions = sessions
        self._embedding = embedding
        self._max_chunks_per_document = max_chunks_per_document

    async def retrieve(
        self,
        query: RetrievalQuery,
        *,
        experiment_mode: RetrievalExperimentMode = RetrievalExperimentMode.RRF_HEURISTIC,
    ) -> list[RetrievedChunk]:
        """执行混合检索，返回 top_k 个去重后的 RetrievedChunk。

        步骤：
            1. 查询归一化
            2. 向量检索（pgvector cosine_distance）
            3. 全文检索（PostgreSQL websearch_to_tsquery）— 仅 HYBRID 模式
            4. RRF 融合两路排名
            5. 后处理：文档去重 + 去相邻 chunk
            6. 截取 top_k
        """
        diagnostics = await self._retrieve_result(query, experiment_mode=experiment_mode)
        return list(diagnostics.final_results)

    async def retrieve_with_diagnostics(
        self,
        query: RetrievalQuery,
        *,
        experiment_mode: RetrievalExperimentMode = RetrievalExperimentMode.RRF_HEURISTIC,
        query_variants: tuple[str, ...] | None = None,
        adjacent_filter_strategy: AdjacentFilterStrategy = AdjacentFilterStrategy.CURRENT,
        candidate_expansion: CandidateExpansionStrategy = CandidateExpansionStrategy.NONE,
    ) -> RetrievalDiagnostics:
        """Return stage diagnostics; query variants are restricted to eval callers."""
        return await self._retrieve_result(
            query,
            experiment_mode=experiment_mode,
            query_variants=query_variants,
            adjacent_filter_strategy=adjacent_filter_strategy,
            candidate_expansion=candidate_expansion,
        )

    async def _retrieve_result(
        self,
        query: RetrievalQuery,
        *,
        experiment_mode: RetrievalExperimentMode,
        query_variants: tuple[str, ...] | None = None,
        adjacent_filter_strategy: AdjacentFilterStrategy = AdjacentFilterStrategy.CURRENT,
        candidate_expansion: CandidateExpansionStrategy = CandidateExpansionStrategy.NONE,
    ) -> RetrievalDiagnostics:
        normalized = normalize_query(query.query)
        if not normalized:
            return RetrievalDiagnostics((), (), (), (), (), (), (), ())

        # 并行执行向量和全文检索（注意：这里实际上是串行的，优化空间）
        async with self._sessions() as session:
            vector_candidates: list[_Candidate] = []
            heading_candidates: list[_Candidate] = []
            if experiment_mode is not RetrievalExperimentMode.TEXT_ONLY:
                variants = tuple(
                    dict.fromkeys(
                        value
                        for item in (query_variants or (normalized,))
                        if (value := normalize_query(item))
                    )
                )
                ranked_variants = [
                    await self._vector_candidates(session, query, variant) for variant in variants
                ]
                vector_candidates = _merge_query_variant_candidates(
                    ranked_variants,
                    candidate_k=query.candidate_k,
                )
                if candidate_expansion in {
                    CandidateExpansionStrategy.HEADING_LEXICAL,
                    CandidateExpansionStrategy.HEADING_SHADOW,
                }:
                    heading_candidates = await self._heading_candidates(session, query, normalized)
                if candidate_expansion is CandidateExpansionStrategy.HEADING_LEXICAL:
                    vector_candidates = _merge_query_variant_candidates(
                        [vector_candidates, heading_candidates],
                        candidate_k=query.candidate_k,
                    )
            text_candidates: list[_Candidate] = []
            if (
                experiment_mode is not RetrievalExperimentMode.VECTOR_ONLY
                and query.mode is RetrievalMode.HYBRID
            ):
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

        # RRF 融合：综合两路排名计算召回分数
        fused = reciprocal_rank_fusion([list(vector_ranks), list(text_ranks)])
        heuristic_scores = {
            chunk_id: _rerank_score(
                normalized=normalized,
                content=by_id[chunk_id].chunk.content,
                fused_score=fused[chunk_id],
                vector_score=vector_scores.get(chunk_id),
                text_score=text_scores.get(chunk_id),
            )
            for chunk_id in fused
        }
        if experiment_mode is RetrievalExperimentMode.VECTOR_ONLY:
            final_scores = vector_scores
        elif experiment_mode is RetrievalExperimentMode.TEXT_ONLY:
            final_scores = text_scores
        elif experiment_mode is RetrievalExperimentMode.RRF:
            final_scores = fused
        else:
            final_scores = heuristic_scores
        ordered_ids = sorted(
            final_scores,
            key=lambda chunk_id: (
                final_scores[chunk_id],
                fused.get(chunk_id, 0.0),
                vector_scores.get(chunk_id) or 0.0,
                text_scores.get(chunk_id) or 0.0,
            ),
            reverse=True,
        )

        converted = {
            chunk_id: _to_retrieved_chunk(
                candidate=by_id[chunk_id],
                normalized=normalized,
                score=final_scores[chunk_id],
                fused_score=fused[chunk_id],
                heuristic_score=heuristic_scores[chunk_id],
                vector_rank=vector_ranks.get(chunk_id),
                text_rank=text_ranks.get(chunk_id),
                vector_score=vector_scores.get(chunk_id),
                text_score=text_scores.get(chunk_id),
            )
            for chunk_id in ordered_ids
        }
        # 后处理：完整执行 diversity filter，再截断。前 top_k 与旧的遇满即停逻辑相同；
        # 继续处理尾部仅用于诊断，不会改变生产返回值。
        post_filter: list[RetrievedChunk] = []
        filtered_out: list[FilteredRetrievalCandidate] = []
        per_document: dict[UUID, int] = {}  # 每篇文档已选 chunk 计数
        selected_by_position: dict[tuple[UUID, int], RetrievedChunk] = {}
        for chunk_id in ordered_ids:
            candidate = by_id[chunk_id]
            document_id = candidate.document.id
            retrieved = converted[chunk_id]

            # 每篇文档最多 max_chunks_per_document 个 chunk
            if (
                self._max_chunks_per_document is not None
                and per_document.get(document_id, 0) >= self._max_chunks_per_document
            ):
                filtered_out.append(
                    FilteredRetrievalCandidate(retrieved, RetrievalFilterReason.PER_DOCUMENT_LIMIT)
                )
                continue

            # 跳过相邻 chunk：避免返回内容高度重叠的连续分块
            neighbor_key = (document_id, candidate.chunk.chunk_index)
            previous = selected_by_position.get((document_id, candidate.chunk.chunk_index - 1))
            should_filter_adjacent = previous is not None and (
                adjacent_filter_strategy is AdjacentFilterStrategy.CURRENT
                or previous.heading_path == retrieved.heading_path
            )
            if should_filter_adjacent:
                filtered_out.append(
                    FilteredRetrievalCandidate(retrieved, RetrievalFilterReason.ADJACENT_CHUNK)
                )
                continue
            selected_by_position[neighbor_key] = retrieved
            per_document[document_id] = per_document.get(document_id, 0) + 1

            post_filter.append(retrieved)

        results = post_filter[: query.top_k]
        filtered_out.extend(
            FilteredRetrievalCandidate(chunk, RetrievalFilterReason.TOP_K_CUTOFF)
            for chunk in post_filter[query.top_k :]
        )
        shadow_heading_candidates = (
            tuple(
                _to_retrieved_chunk(
                    candidate=item,
                    normalized=normalized,
                    score=item.score,
                    fused_score=0.0,
                    heuristic_score=0.0,
                    vector_rank=None,
                    text_rank=None,
                    vector_score=None,
                    text_score=None,
                    heading_rank=item.rank,
                    heading_score=item.score,
                )
                for item in heading_candidates
            )
            if candidate_expansion is CandidateExpansionStrategy.HEADING_SHADOW
            else ()
        )
        primary_candidate_ids = {item.chunk.id for item in vector_candidates}
        supplemental_candidates = tuple(
            item for item in shadow_heading_candidates if item.chunk_id not in primary_candidate_ids
        )
        return RetrievalDiagnostics(
            vector_candidates=tuple(converted[item.chunk.id] for item in vector_candidates),
            heading_candidates=(
                shadow_heading_candidates
                or tuple(
                    converted[item.chunk.id]
                    for item in heading_candidates
                    if item.chunk.id in converted
                )
            ),
            text_candidates=tuple(converted[item.chunk.id] for item in text_candidates),
            ordered_candidates=tuple(converted[chunk_id] for chunk_id in ordered_ids),
            post_filter_candidates=tuple(post_filter),
            filtered_out=tuple(filtered_out),
            final_results=tuple(results),
            supplemental_candidates=supplemental_candidates,
        )

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
                KnowledgeChunkModel.is_active.is_(True),
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
        if _contains_cjk(normalized):
            return await self._bigram_text_candidates(session, query, normalized)
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

    async def _heading_candidates(
        self, session: AsyncSession, query: RetrievalQuery, normalized: str
    ) -> list[_Candidate]:
        """Eval-only lexical recall over heading_path and document title."""
        terms = _lexical_terms(normalized)
        if not terms:
            return []
        heading_text = cast(KnowledgeChunkModel.heading_path, String)
        conditions = [
            or_(
                heading_text.ilike(f"%{term}%"),
                SourceDocumentModel.title.ilike(f"%{term}%"),
            )
            for term in terms
        ]
        rank_expr = literal(0.0)
        for term, condition in zip(terms, conditions, strict=True):
            weight = 2.0 if _contains_cjk(term) else 1.0
            rank_expr = rank_expr + case((condition, weight), else_=0.0)
        rank_expr = rank_expr.label("heading_rank")
        rows = (
            await session.execute(
                self._base_query(query)
                .add_columns(rank_expr)
                .where(or_(*conditions))
                .order_by(rank_expr.desc(), KnowledgeChunkModel.chunk_index)
                .limit(query.candidate_k)
            )
        ).all()
        return [
            _Candidate(chunk=chunk, document=document, rank=rank, score=float(score))
            for rank, (chunk, document, score) in enumerate(rows, start=1)
        ]

    async def _bigram_text_candidates(
        self, session: AsyncSession, query: RetrievalQuery, normalized: str
    ) -> list[_Candidate]:
        """中文轻量全文召回：用应用层 bigram/关键词转 SQL ILIKE 条件。

        这不是企业级中文分词的最终形态，但能在不引入 PostgreSQL 插件的情况下，
        让中文资料具备可解释的词面召回信号。
        """
        terms = _lexical_terms(normalized)
        if not terms:
            return []

        conditions = [KnowledgeChunkModel.content.ilike(f"%{term}%") for term in terms]
        rank_expr = literal(0.0)
        for term, condition in zip(terms, conditions, strict=True):
            weight = 2.0 if _contains_cjk(term) else 1.0
            rank_expr = rank_expr + case((condition, weight), else_=0.0)
        rank_expr = rank_expr.label("bigram_rank")

        rows = (
            await session.execute(
                self._base_query(query)
                .add_columns(rank_expr)
                .where(or_(*conditions))
                .order_by(rank_expr.desc(), KnowledgeChunkModel.chunk_index)
                .limit(query.candidate_k)
            )
        ).all()
        return [
            _Candidate(chunk=chunk, document=document, rank=rank, score=float(score))
            for rank, (chunk, document, score) in enumerate(rows, start=1)
        ]


def _to_retrieved_chunk(
    *,
    candidate: _Candidate,
    normalized: str,
    score: float,
    fused_score: float,
    heuristic_score: float,
    vector_rank: int | None,
    text_rank: int | None,
    vector_score: float | None,
    text_score: float | None,
    heading_rank: int | None = None,
    heading_score: float | None = None,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=candidate.chunk.id,
        document_id=candidate.document.id,
        document_title=candidate.document.title,
        source_url=candidate.document.source_url,
        trust_level=str(candidate.document.trust_level),
        heading_path=tuple(candidate.chunk.heading_path),
        page_number=candidate.chunk.page_number,
        block_type=_infer_retrieved_block_type(candidate.chunk.content),
        chunk_index=candidate.chunk.chunk_index,
        content=candidate.chunk.content,
        score=score,
        retrieval_explanation=_retrieval_explanation(
            fused_score=fused_score,
            rerank_score=heuristic_score,
            lexical_overlap=_lexical_overlap(normalized, candidate.chunk.content),
            vector_rank=vector_rank,
            text_rank=text_rank,
            vector_score=vector_score,
            text_score=text_score,
        ),
        vector_rank=vector_rank,
        text_rank=text_rank,
        vector_score=vector_score,
        text_score=text_score,
        document_logical_name=candidate.document.logical_name,
        rrf_score=fused_score,
        heuristic_rerank_score=heuristic_score,
        heading_rank=heading_rank,
        heading_score=heading_score,
    )


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
    rerank_score: float,
    lexical_overlap: float,
    vector_rank: int | None,
    text_rank: int | None,
    vector_score: float | None,
    text_score: float | None,
) -> str:
    """生成检索结果的可读解释字符串。

    格式示例："RRF=0.0328 | vector_rank=1 | text_rank=3 | vector_score=0.8560 | text_score=0.4320"
    """
    signals: list[str] = [f"RRF={fused_score:.4f}", f"rerank={rerank_score:.4f}"]
    if lexical_overlap > 0:
        signals.append(f"lexical_overlap={lexical_overlap:.2f}")
    if vector_rank is not None:
        signals.append(f"vector_rank={vector_rank}")
    if text_rank is not None:
        signals.append(f"text_rank={text_rank}")
    if vector_score is not None:
        signals.append(f"vector_score={vector_score:.4f}")
    if text_score is not None:
        signals.append(f"text_score={text_score:.4f}")
    return " | ".join(signals)


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _lexical_terms(text: str, *, limit: int = 16) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        normalized = term.strip().lower()
        if len(normalized) < 2 or normalized in seen:
            return
        seen.add(normalized)
        terms.append(normalized)

    for token in re.findall(r"[a-zA-Z0-9_+#.-]{2,}", text):
        add(token)
    for segment in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        add(segment)
        for index in range(len(segment) - 1):
            add(segment[index : index + 2])
    return terms[:limit]


def _lexical_overlap(query: str, content: str) -> float:
    terms = _lexical_terms(query)
    if not terms:
        return 0.0
    lowered = content.lower()
    hits = sum(1 for term in terms if term in lowered)
    return hits / len(terms)


def _rerank_score(
    *,
    normalized: str,
    content: str,
    fused_score: float,
    vector_score: float | None,
    text_score: float | None,
) -> float:
    lexical = _lexical_overlap(normalized, content)
    vector_boost = max(0.0, min(vector_score or 0.0, 1.0)) * 0.003
    text_boost = min(text_score or 0.0, 10.0) / 10.0 * 0.004
    lexical_boost = lexical * 0.006
    return fused_score + vector_boost + text_boost + lexical_boost

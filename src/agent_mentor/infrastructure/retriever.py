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
    chunk: KnowledgeChunkModel
    document: SourceDocumentModel
    rank: int
    score: float


class PostgresHybridRetriever:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        embedding: EmbeddingGateway,
        *,
        max_chunks_per_document: int,
    ) -> None:
        self._sessions = sessions
        self._embedding = embedding
        self._max_chunks_per_document = max_chunks_per_document

    async def retrieve(self, query: RetrievalQuery) -> list[RetrievedChunk]:
        normalized = normalize_query(query.query)
        if not normalized:
            return []
        async with self._sessions() as session:
            vector_candidates = await self._vector_candidates(session, query, normalized)
            text_candidates: list[_Candidate] = []
            if query.mode is RetrievalMode.HYBRID:
                text_candidates = await self._text_candidates(session, query, normalized)
        by_id = {
            candidate.chunk.id: candidate for candidate in [*vector_candidates, *text_candidates]
        }
        vector_ranks = {candidate.chunk.id: candidate.rank for candidate in vector_candidates}
        text_ranks = {candidate.chunk.id: candidate.rank for candidate in text_candidates}
        vector_scores = {candidate.chunk.id: candidate.score for candidate in vector_candidates}
        text_scores = {candidate.chunk.id: candidate.score for candidate in text_candidates}
        fused = reciprocal_rank_fusion([list(vector_ranks), list(text_ranks)])
        ordered_ids = sorted(fused, key=lambda chunk_id: fused[chunk_id], reverse=True)

        results: list[RetrievedChunk] = []
        per_document: dict[UUID, int] = {}
        seen_neighbors: set[tuple[UUID, int]] = set()
        for chunk_id in ordered_ids:
            candidate = by_id[chunk_id]
            document_id = candidate.document.id
            if per_document.get(document_id, 0) >= self._max_chunks_per_document:
                continue
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
                    ).op("@@")(ts_query)
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

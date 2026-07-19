from __future__ import annotations

import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.api.errors import AppError
from agent_mentor.infrastructure.database.models import (
    ChatCitationModel,
    ChatMessageModel,
    ChatSessionModel,
)
from agent_mentor.ports.knowledge_retriever import (
    KnowledgeRetriever,
    RetrievalQuery,
    RetrievedChunk,
)
from agent_mentor.rag.retrieval import validate_citations

ENGLISH_STOPWORDS = {
    "about",
    "and",
    "are",
    "did",
    "does",
    "for",
    "from",
    "how",
    "into",
    "the",
    "this",
    "what",
    "when",
    "where",
    "which",
    "why",
    "with",
}


@dataclass(frozen=True, slots=True)
class AnswerResult:
    session_id: UUID
    message_id: UUID
    answer: str
    citations: tuple[RetrievedChunk, ...]
    candidates: tuple[RetrievedChunk, ...]
    evidence_sufficient: bool


class AnswerService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        retriever: KnowledgeRetriever,
        *,
        default_top_k: int,
        default_candidate_k: int,
        min_evidence_score: float,
    ) -> None:
        self._sessions = sessions
        self._retriever = retriever
        self._default_top_k = default_top_k
        self._default_candidate_k = default_candidate_k
        self._min_evidence_score = min_evidence_score

    async def answer(
        self,
        *,
        knowledge_base_id: UUID,
        question: str,
        top_k: int | None = None,
        candidate_k: int | None = None,
        allow_model_knowledge: bool = False,
    ) -> AnswerResult:
        candidates = await self._retriever.retrieve(
            RetrievalQuery(
                knowledge_base_id=knowledge_base_id,
                query=question,
                top_k=top_k or self._default_top_k,
                candidate_k=candidate_k or self._default_candidate_k,
            )
        )
        sufficient = (
            bool(candidates)
            and candidates[0].score >= self._min_evidence_score
            and self._has_lexical_support(question, candidates)
        )
        if not sufficient and not allow_model_knowledge:
            answer = (
                "当前知识库证据不足，我不能把模型常识伪装成资料结论。"
                "你可以补充资料后再问，或允许模型补充并明确标记。"
            )
            return await self._persist(
                knowledge_base_id=knowledge_base_id,
                question=question,
                answer=answer,
                candidates=candidates,
                citations=[],
                evidence_sufficient=False,
            )

        citations = candidates[: min(3, len(candidates))]
        answer = self._compose_grounded_answer(
            question, citations, allow_model_knowledge and not sufficient
        )
        validate_citations([chunk.chunk_id for chunk in citations], candidates)
        return await self._persist(
            knowledge_base_id=knowledge_base_id,
            question=question,
            answer=answer,
            candidates=candidates,
            citations=citations,
            evidence_sufficient=sufficient,
        )

    async def answer_events(self, **kwargs: object) -> AsyncIterator[dict[str, object]]:
        yield {"event": "retrieval.started", "data": {"question": kwargs.get("question")}}
        try:
            result = await self.answer(**kwargs)  # type: ignore[arg-type]
            yield {
                "event": "retrieval.completed",
                "data": {"candidate_count": len(result.candidates)},
            }
            for token in result.answer.split():
                yield {"event": "answer.delta", "data": token}
            yield {
                "event": "answer.references",
                "data": [str(chunk.chunk_id) for chunk in result.citations],
            }
            yield {"event": "answer.completed", "data": {"message_id": str(result.message_id)}}
        except Exception as error:
            yield {"event": "answer.failed", "data": {"error": str(error)}}

    def _compose_grounded_answer(
        self, question: str, citations: list[RetrievedChunk], uses_model_knowledge: bool
    ) -> str:
        del question
        if not citations:
            return (
                "模型补充：当前知识库没有足够证据，下面只能给出一般性学习建议，"
                "不能作为资料引用结论。"
            )
        lines = ["基于当前知识库，我整理到的答案是："]
        for index, chunk in enumerate(citations, start=1):
            excerpt = chunk.content.strip().replace("\n", " ")
            if len(excerpt) > 220:
                excerpt = f"{excerpt[:217]}..."
            lines.append(f"{index}. {excerpt} [chunk:{chunk.chunk_id}]")
        if uses_model_knowledge:
            lines.append("模型补充：以上引用不足以完整覆盖问题，未引用部分仅作为一般性补充。")
        lines.append("引用已限制在本次检索上下文内。")
        return "\n".join(lines)

    def _has_lexical_support(self, question: str, candidates: list[RetrievedChunk]) -> bool:
        query_terms = self._evidence_terms(question)
        if not query_terms:
            return True
        context_terms: set[str] = set()
        for chunk in candidates[:3]:
            context_terms.update(self._evidence_terms(chunk.content))
            context_terms.update(term.lower() for term in chunk.heading_path)
            context_terms.add(chunk.document_title.lower())
        return bool(query_terms & context_terms)

    def _evidence_terms(self, text: str) -> set[str]:
        lowered = text.lower()
        terms = {
            match.group(0)
            for match in re.finditer(r"[a-z0-9_]{2,}", lowered)
            if match.group(0) not in ENGLISH_STOPWORDS
        }
        for segment in re.findall(r"[\u4e00-\u9fff]{2,}", lowered):
            terms.update(segment[index : index + 2] for index in range(0, len(segment) - 1))
        return terms

    async def _persist(
        self,
        *,
        knowledge_base_id: UUID,
        question: str,
        answer: str,
        candidates: list[RetrievedChunk],
        citations: list[RetrievedChunk],
        evidence_sufficient: bool,
    ) -> AnswerResult:
        now = datetime.now(UTC)
        session_id = uuid4()
        assistant_message_id = uuid4()
        diagnostics = {
            "candidate_count": len(candidates),
            "evidence_sufficient": evidence_sufficient,
            "candidates": [
                {
                    "chunk_id": str(chunk.chunk_id),
                    "score": chunk.score,
                    "vector_rank": chunk.vector_rank,
                    "text_rank": chunk.text_rank,
                }
                for chunk in candidates
            ],
        }
        async with self._sessions() as session:
            session.add(
                ChatSessionModel(
                    id=session_id,
                    knowledge_base_id=knowledge_base_id,
                    title=question[:120],
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                ChatMessageModel(
                    id=uuid4(),
                    session_id=session_id,
                    role="user",
                    content=question,
                    retrieval_diagnostics=None,
                    created_at=now,
                )
            )
            session.add(
                ChatMessageModel(
                    id=assistant_message_id,
                    session_id=session_id,
                    role="assistant",
                    content=answer,
                    retrieval_diagnostics=diagnostics,
                    created_at=now,
                )
            )
            for position, chunk in enumerate(citations, start=1):
                session.add(
                    ChatCitationModel(
                        id=uuid4(),
                        message_id=assistant_message_id,
                        chunk_id=chunk.chunk_id,
                        position=position,
                        quote=chunk.content[:500],
                        created_at=now,
                    )
                )
            await session.commit()
        return AnswerResult(
            session_id=session_id,
            message_id=assistant_message_id,
            answer=answer,
            citations=tuple(citations),
            candidates=tuple(candidates),
            evidence_sufficient=evidence_sufficient,
        )


def ensure_citations_are_valid(citation_ids: list[UUID], context: list[RetrievedChunk]) -> None:
    try:
        validate_citations(citation_ids, context)
    except ValueError as error:
        raise AppError(
            "LLM_OUTPUT_INVALID", "Citation validation failed.", detail=str(error)
        ) from error

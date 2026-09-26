from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.api.errors import AppError
from agent_mentor.infrastructure.database.models import (
    ChatCitationModel,
    ChatMessageModel,
    ChatSessionModel,
)
from agent_mentor.logging import log_event
from agent_mentor.ports.knowledge_retriever import (
    KnowledgeRetriever,
    RetrievalQuery,
    RetrievedChunk,
)
from agent_mentor.ports.llm_gateway import LLMGateway, Message, ModelPolicy, TraceContext
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

CHINESE_STOP_BIGRAMS = {
    "为什么",
    "什么问",
    "问题",
    "如何",
    "需要",
    "同时",
    "使用",
    "说明",
    "根据",
    "资料",
    "中的",
    "怎么",
    "哪些",
    "是否",
}

GENERIC_EVIDENCE_TERMS = {
    "agent",
    "ai",
    "api",
    "desktop",
    "docker",
    "llm",
    "rag",
    "设计",
    "系统",
    "项目",
    "统设",
    "实现",
    "影响",
    "说明",
    "什么",
}

STRONG_ENGLISH_EVIDENCE_TERMS = {
    "chunk_id",
    "mrr",
    "recall",
    "rrf",
    "sse",
}


@dataclass(frozen=True, slots=True)
class AnswerResult:
    session_id: UUID
    message_id: UUID
    answer: str
    citations: tuple[RetrievedChunk, ...]
    candidates: tuple[RetrievedChunk, ...]
    evidence_sufficient: bool
    generation_mode: str
    model_name: str | None
    fallback_reason: str | None


class EvidenceDecision(StrEnum):
    """Evaluation vocabulary for evidence coverage.

    The current production policy is binary and therefore emits only ``full``
    or ``none``. ``partial`` is reserved for evaluation policies that can
    explicitly detect an uncovered part of a question.
    """

    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class CandidateEvidenceAssessment:
    chunk_id: str
    score: float
    lexical_support: bool
    covered_terms: tuple[str, ...]
    specific_covered_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    policy_name: str
    decision: EvidenceDecision
    production_sufficient: bool
    supported_chunk_ids: tuple[str, ...]
    top_supported_score: float | None
    query_terms: tuple[str, ...]
    specific_query_terms: tuple[str, ...]
    covered_terms: tuple[str, ...]
    uncovered_terms: tuple[str, ...]
    coverage_ratio: float
    numeric_tokens_requested: tuple[str, ...]
    numeric_tokens_covered: tuple[str, ...]
    demand_markers: tuple[str, ...]
    candidate_assessments: tuple[CandidateEvidenceAssessment, ...]
    rejection_reasons: tuple[str, ...]


class GroundedAnswerOutput(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
    citation_chunk_ids: list[UUID] = Field(default_factory=list)
    evidence_sufficient: bool


class AnswerService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        retriever: KnowledgeRetriever,
        llm: LLMGateway | None = None,
        *,
        default_top_k: int,
        default_candidate_k: int,
        min_evidence_score: float,
        default_model: str | None = None,
    ) -> None:
        self._sessions = sessions
        self._retriever = retriever
        self._llm = llm
        self._default_top_k = default_top_k
        self._default_candidate_k = default_candidate_k
        self._min_evidence_score = min_evidence_score
        self._default_model = default_model

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
        supported_candidates, sufficient = self.assess_evidence(question, candidates)
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
                generation_mode="evidence_guard",
                model_name=None,
                fallback_reason="insufficient_evidence",
            )

        # Citations must be both retrieved and lexically related to the question.
        # A whitelist check alone only proves provenance, not semantic support.
        citations = supported_candidates[: min(3, len(supported_candidates))]
        (
            answer,
            generation_mode,
            fallback_reason,
            effective_sufficient,
        ) = await self._generate_answer(
            question=question,
            candidates=supported_candidates if sufficient else [],
            citations=citations,
            evidence_sufficient=sufficient,
            allow_model_knowledge=allow_model_knowledge,
        )
        validate_citations([chunk.chunk_id for chunk in citations], candidates)
        return await self._persist(
            knowledge_base_id=knowledge_base_id,
            question=question,
            answer=answer,
            candidates=candidates,
            citations=citations,
            evidence_sufficient=effective_sufficient,
            generation_mode=generation_mode,
            model_name=self._default_model if generation_mode == "llm" else None,
            fallback_reason=fallback_reason,
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
            log_event(
                logging.WARNING,
                "rag_answer.stream_failed",
                error_type=type(error).__name__,
                fallback="sse_error_event",
            )
            yield {"event": "answer.failed", "data": {"error": str(error)}}

    async def _generate_answer(
        self,
        *,
        question: str,
        candidates: list[RetrievedChunk],
        citations: list[RetrievedChunk],
        evidence_sufficient: bool,
        allow_model_knowledge: bool,
    ) -> tuple[str, str, str | None, bool]:
        if self._llm is None:
            return (
                self._compose_grounded_answer(
                    question, citations, allow_model_knowledge and not evidence_sufficient
                ),
                "deterministic",
                "llm_not_configured",
                evidence_sufficient,
            )
        try:
            output = await self._llm.generate_structured(
                operation="rag_answer",
                messages=[
                    Message(
                        role="system",
                        content=(
                            "你是 AgentMentor 的学习辅导助手。必须优先基于给定资料回答。"
                            "如果引用资料，请只使用候选资料里的 chunk_id；不要编造引用。"
                            "如果资料不足但允许模型补充，要明确写出“模型补充”。"
                        ),
                    ),
                    Message(
                        role="user",
                        content=self._answer_prompt(
                            question, candidates, evidence_sufficient, allow_model_knowledge
                        ),
                    ),
                ],
                response_model=GroundedAnswerOutput,
                model_policy=ModelPolicy(model=self._default_model),
                trace_context=TraceContext(trace_id=str(uuid4()), operation="rag_answer"),
            )
            ensure_citations_are_valid(output.citation_chunk_ids, candidates)
            if not output.evidence_sufficient and not allow_model_knowledge:
                citations.clear()
                return (
                    "当前知识库检索到了候选内容，但这些证据不足以可靠回答该问题。"
                    "请补充相关资料或调整问题后重试。",
                    "evidence_guard",
                    "llm_rejected_evidence",
                    False,
                )
            selected = [
                chunk for chunk in candidates if chunk.chunk_id in output.citation_chunk_ids
            ]
            if output.evidence_sufficient and not selected and candidates:
                selected = candidates[:1]
            citations[:] = selected[:3]
            return output.answer, "llm", None, evidence_sufficient
        except Exception as error:
            log_event(
                logging.WARNING,
                "rag_answer.llm_fallback",
                error_type=type(error).__name__,
                fallback="deterministic_grounded_answer",
                candidate_count=len(candidates),
                evidence_sufficient=evidence_sufficient,
            )
            return (
                self._compose_grounded_answer(
                    question, citations, allow_model_knowledge and not evidence_sufficient
                ),
                "deterministic",
                type(error).__name__,
                evidence_sufficient,
            )

    def _answer_prompt(
        self,
        question: str,
        candidates: list[RetrievedChunk],
        evidence_sufficient: bool,
        allow_model_knowledge: bool,
    ) -> str:
        context = []
        for index, chunk in enumerate(candidates[:6], start=1):
            context.append(
                "\n".join(
                    [
                        f"资料 {index}",
                        f"chunk_id: {chunk.chunk_id}",
                        f"document: {chunk.document_title}",
                        f"heading: {' > '.join(chunk.heading_path)}",
                        f"score: {chunk.score}",
                        f"content: {chunk.content[:1200]}",
                    ]
                )
            )
        return (
            f"用户问题：{question}\n"
            f"证据是否足够：{evidence_sufficient}\n"
            f"是否允许模型补充：{allow_model_knowledge}\n\n"
            "候选资料：\n"
            f"{chr(10).join(context) if context else '无'}\n\n"
            "请输出 JSON：answer、citation_chunk_ids、evidence_sufficient。"
        )

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
        overlap = query_terms & context_terms
        english_query_terms = {term for term in query_terms if term.isascii()}
        chinese_query_terms = query_terms - english_query_terms
        chinese_overlap = overlap - english_query_terms
        if english_query_terms & overlap:
            strong_english_overlap = english_query_terms & overlap & STRONG_ENGLISH_EVIDENCE_TERMS
            return bool(strong_english_overlap) or not self._requires_specific_chinese_support(
                chinese_query_terms, chinese_overlap
            )
        if not chinese_query_terms:
            return False
        specific_chinese_overlap = chinese_overlap - GENERIC_EVIDENCE_TERMS
        return len(specific_chinese_overlap) >= 2 and (
            len(chinese_overlap) / len(chinese_query_terms) >= 0.18
        )

    def _requires_specific_chinese_support(
        self, chinese_query_terms: set[str], chinese_overlap: set[str]
    ) -> bool:
        if len(chinese_query_terms) < 4:
            return False
        specific_query_terms = chinese_query_terms - GENERIC_EVIDENCE_TERMS
        if len(specific_query_terms) < 3:
            return False
        specific_overlap = chinese_overlap - GENERIC_EVIDENCE_TERMS
        return not specific_overlap

    def _supported_candidates(
        self, question: str, candidates: list[RetrievedChunk]
    ) -> list[RetrievedChunk]:
        return [
            candidate
            for candidate in candidates
            if self._has_lexical_support(question, [candidate])
        ]

    def assess_evidence(
        self, question: str, candidates: list[RetrievedChunk]
    ) -> tuple[list[RetrievedChunk], bool]:
        assessment = self.assess_evidence_diagnostics(question, candidates)
        supported_ids = set(assessment.supported_chunk_ids)
        return (
            [candidate for candidate in candidates if str(candidate.chunk_id) in supported_ids],
            assessment.production_sufficient,
        )

    def assess_evidence_diagnostics(
        self, question: str, candidates: list[RetrievedChunk]
    ) -> EvidenceAssessment:
        """Explain the current Gate without changing its decision."""
        query_terms = self._evidence_terms(question)
        specific_query_terms = query_terms - GENERIC_EVIDENCE_TERMS
        candidate_rows: list[CandidateEvidenceAssessment] = []
        supported_candidates: list[RetrievedChunk] = []
        covered_terms: set[str] = set()
        for candidate in candidates:
            context_terms = self._evidence_terms(candidate.content)
            context_terms.update(self._evidence_terms(" ".join(candidate.heading_path)))
            context_terms.update(self._evidence_terms(candidate.document_title))
            overlap = query_terms & context_terms
            lexical_support = self._has_lexical_support(question, [candidate])
            if lexical_support:
                supported_candidates.append(candidate)
                covered_terms.update(overlap)
            candidate_rows.append(
                CandidateEvidenceAssessment(
                    chunk_id=str(candidate.chunk_id),
                    score=candidate.score,
                    lexical_support=lexical_support,
                    covered_terms=tuple(sorted(overlap)),
                    specific_covered_terms=tuple(sorted(overlap & specific_query_terms)),
                )
            )
        top_supported_score = supported_candidates[0].score if supported_candidates else None
        sufficient = bool(supported_candidates) and bool(
            top_supported_score is not None and top_supported_score >= self._min_evidence_score
        )
        numeric_tokens = set(re.findall(r"\d+(?:\.\d+)?%?", question))
        covered_numeric_tokens = {
            token
            for token in numeric_tokens
            if any(token in candidate.content for candidate in supported_candidates)
        }
        demand_markers = tuple(
            marker
            for marker in (
                "精确值",
                "多少",
                "哪一天",
                "保证",
                "一定",
                "最好",
                "相比",
                "下一版",
                "未来",
                "当前",
            )
            if marker in question
        )
        rejection_reasons: list[str] = []
        if not supported_candidates:
            rejection_reasons.append("no_lexically_supported_candidate")
        elif not sufficient:
            rejection_reasons.append("top_supported_score_below_threshold")
        return EvidenceAssessment(
            policy_name="current_binary_v1",
            decision=EvidenceDecision.FULL if sufficient else EvidenceDecision.NONE,
            production_sufficient=sufficient,
            supported_chunk_ids=tuple(str(item.chunk_id) for item in supported_candidates),
            top_supported_score=top_supported_score,
            query_terms=tuple(sorted(query_terms)),
            specific_query_terms=tuple(sorted(specific_query_terms)),
            covered_terms=tuple(sorted(covered_terms)),
            uncovered_terms=tuple(sorted(query_terms - covered_terms)),
            coverage_ratio=(
                round(len(covered_terms) / len(query_terms), 4) if query_terms else 1.0
            ),
            numeric_tokens_requested=tuple(sorted(numeric_tokens)),
            numeric_tokens_covered=tuple(sorted(covered_numeric_tokens)),
            demand_markers=demand_markers,
            candidate_assessments=tuple(candidate_rows),
            rejection_reasons=tuple(rejection_reasons),
        )

    def _evidence_terms(self, text: str) -> set[str]:
        lowered = text.lower()
        terms = {
            match.group(0)
            for match in re.finditer(r"[a-z0-9_]{2,}", lowered)
            if match.group(0) not in ENGLISH_STOPWORDS
        }
        for segment in re.findall(r"[\u4e00-\u9fff]{2,}", lowered):
            terms.update(
                bigram
                for index in range(0, len(segment) - 1)
                if (bigram := segment[index : index + 2]) not in CHINESE_STOP_BIGRAMS
            )
        if "rrf" in terms or "reciprocal rank fusion" in lowered:
            terms.update({"rrf", "reciprocal", "rank", "fusion"})
        if "全文检索" in lowered:
            terms.update({"lexical", "fulltext", "全文", "检索"})
        if "向量检索" in lowered:
            terms.update({"vector", "embedding", "向量", "检索"})
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
        generation_mode: str,
        model_name: str | None,
        fallback_reason: str | None,
    ) -> AnswerResult:
        now = datetime.now(UTC)
        session_id = uuid4()
        assistant_message_id = uuid4()
        diagnostics = {
            "candidate_count": len(candidates),
            "evidence_sufficient": evidence_sufficient,
            "llm_enabled": self._llm is not None,
            "generation_mode": generation_mode,
            "model_name": model_name,
            "fallback_reason": fallback_reason,
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
            generation_mode=generation_mode,
            model_name=model_name,
            fallback_reason=fallback_reason,
        )


def ensure_citations_are_valid(citation_ids: list[UUID], context: list[RetrievedChunk]) -> None:
    try:
        validate_citations(citation_ids, context)
    except ValueError as error:
        raise AppError(
            "LLM_OUTPUT_INVALID", "Citation validation failed.", detail=str(error)
        ) from error

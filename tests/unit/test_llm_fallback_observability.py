from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, TypeVar, cast
from uuid import uuid4

import pytest
from pydantic import BaseModel

from agent_mentor.application.answer_service import AnswerService
from agent_mentor.infrastructure.fakes import FakeLLMGateway
from agent_mentor.ports.knowledge_retriever import RetrievedChunk
from agent_mentor.ports.llm_gateway import Message, ModelPolicy, TraceContext


def chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="RAG Guide",
        source_url=None,
        trust_level="curated",
        heading_path=("RAG",),
        page_number=None,
        block_type="paragraph",
        chunk_index=0,
        content="RAG uses retrieved evidence and citations.",
        score=0.03,
        retrieval_explanation="RRF=0.0300",
    )


T = TypeVar("T", bound=BaseModel)


class HallucinatedCitationLLM:
    async def generate_structured(
        self,
        *,
        operation: str,
        messages: Sequence[Message],
        response_model: type[T],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
    ) -> T:
        del operation, messages, model_policy, trace_context
        return cast(
            T,
            response_model(
                answer="这是一个带伪造引用的回答。",
                citation_chunk_ids=[uuid4()],
                evidence_sufficient=True,
            ),
        )

    async def stream_text(
        self,
        *,
        operation: str,
        messages: Sequence[Message],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
    ) -> AsyncIterator[str]:
        del operation, messages, model_policy, trace_context
        if False:
            yield ""


@pytest.mark.asyncio
async def test_answer_service_logs_when_llm_answer_falls_back(
    caplog: pytest.LogCaptureFixture,
) -> None:
    evidence = chunk()
    service = AnswerService(
        cast(Any, None),
        cast(Any, None),
        FakeLLMGateway(),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
    )

    with caplog.at_level("WARNING", logger="agent_mentor"):
        answer, mode, reason, evidence_sufficient = await service._generate_answer(  # pyright: ignore[reportPrivateUsage]
            question="RAG 如何提升回答可信度？",
            candidates=[evidence],
            citations=[evidence],
            evidence_sufficient=True,
            allow_model_knowledge=False,
        )

    assert answer
    assert mode == "deterministic"
    assert reason == "RuntimeError"
    assert evidence_sufficient is True
    assert "rag_answer.llm_fallback" in caplog.text
    assert "deterministic_grounded_answer" in caplog.text


@pytest.mark.asyncio
async def test_answer_service_downgrades_when_llm_hallucinates_citation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    evidence = chunk()
    citations = [evidence]
    service = AnswerService(
        cast(Any, None),
        cast(Any, None),
        HallucinatedCitationLLM(),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
    )

    with caplog.at_level("WARNING", logger="agent_mentor"):
        answer, mode, reason, evidence_sufficient = await service._generate_answer(  # pyright: ignore[reportPrivateUsage]
            question="RAG 如何提升回答可信度？",
            candidates=[evidence],
            citations=citations,
            evidence_sufficient=True,
            allow_model_knowledge=False,
        )

    assert answer.startswith("基于当前知识库")
    assert mode == "deterministic"
    assert reason == "AppError"
    assert evidence_sufficient is True
    assert citations == [evidence]
    assert "rag_answer.llm_fallback" in caplog.text
    assert "AppError" in caplog.text

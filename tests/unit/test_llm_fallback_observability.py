from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

import pytest

from agent_mentor.application.answer_service import AnswerService
from agent_mentor.infrastructure.fakes import FakeLLMGateway
from agent_mentor.ports.knowledge_retriever import RetrievedChunk


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
        answer = await service._generate_answer(  # pyright: ignore[reportPrivateUsage]
            question="RAG 如何提升回答可信度？",
            candidates=[evidence],
            citations=[evidence],
            evidence_sufficient=True,
            allow_model_knowledge=False,
        )

    assert answer
    assert "rag_answer.llm_fallback" in caplog.text
    assert "deterministic_grounded_answer" in caplog.text

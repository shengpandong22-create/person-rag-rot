from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

import pytest

from agent_mentor.api.errors import AppError
from agent_mentor.application.answer_service import AnswerService, ensure_citations_are_valid
from agent_mentor.ports.knowledge_retriever import RetrievedChunk
from agent_mentor.rag.retrieval import normalize_query, reciprocal_rank_fusion, validate_citations


def chunk(chunk_id=None) -> RetrievedChunk:  # type: ignore[no-untyped-def]
    return RetrievedChunk(
        chunk_id=chunk_id or uuid4(),
        document_id=uuid4(),
        document_title="RAG Guide",
        source_url=None,
        trust_level="curated",
        heading_path=("RAG",),
        page_number=None,
        chunk_index=0,
        content="RAG uses retrieved evidence.",
        score=0.03,
    )


def test_query_normalization_preserves_java_names() -> None:
    assert (
        normalize_query("  HashMap   NullPointerException  RAG ")
        == "HashMap NullPointerException RAG"
    )


def test_rrf_is_deterministic_for_fixed_rankings() -> None:
    first, second, third = uuid4(), uuid4(), uuid4()

    scores = reciprocal_rank_fusion([[first, second], [second, third]])

    assert scores[second] > scores[first] > scores[third]
    assert scores == reciprocal_rank_fusion([[first, second], [second, third]])


def test_citation_validator_allows_only_current_context() -> None:
    valid = chunk()
    invalid = uuid4()

    validate_citations([valid.chunk_id], [valid])

    with pytest.raises(ValueError):
        validate_citations([invalid], [valid])


def test_answer_citation_validation_maps_to_app_error() -> None:
    valid = chunk()

    with pytest.raises(AppError) as error:
        ensure_citations_are_valid([uuid4()], [valid])

    assert error.value.code == "LLM_OUTPUT_INVALID"


def test_answer_service_requires_lexical_support_for_evidence() -> None:
    service = AnswerService(
        cast(Any, None),
        cast(Any, None),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
    )
    evidence = chunk()

    assert service._has_lexical_support("RAG 如何使用 evidence?", [evidence])
    assert not service._has_lexical_support("我昨天午饭吃了什么?", [evidence])

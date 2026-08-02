from __future__ import annotations

from dataclasses import replace
from typing import Any, cast
from uuid import uuid4

import pytest

from agent_mentor.api.errors import AppError
from agent_mentor.application.answer_service import AnswerService, ensure_citations_are_valid
from agent_mentor.infrastructure.retriever import (
    _infer_retrieved_block_type,
    _retrieval_explanation,
)
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
        block_type="paragraph",
        chunk_index=0,
        content="RAG uses retrieved evidence.",
        score=0.03,
        retrieval_explanation="RRF=0.0300",
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


def test_retrieval_explanation_contains_rank_signals() -> None:
    explanation = _retrieval_explanation(
        fused_score=0.0325,
        vector_rank=1,
        text_rank=3,
        vector_score=0.8123,
        text_score=0.4567,
    )

    assert "RRF=0.0325" in explanation
    assert "vector_rank=1" in explanation
    assert "text_rank=3" in explanation
    assert _infer_retrieved_block_type("| A | B |\n| - | - |\n| x | y |") == "table"


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


def test_answer_service_rejects_incidental_chinese_overlap() -> None:
    service = AnswerService(
        cast(Any, None),
        cast(Any, None),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
    )
    evidence = chunk()
    evidence = replace(evidence, content="评估实验需要根据资料说明模型输出是否可靠。")

    assert not service._has_lexical_support(
        "请根据知识库解释量子纠缠实验中的贝尔不等式。", [evidence]
    )


def test_answer_service_rejects_cross_domain_question_with_generic_safety_terms() -> None:
    service = AnswerService(
        cast(Any, None),
        cast(Any, None),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
    )
    evidence = chunk()
    evidence = replace(evidence, content="Agent 工具调用需要权限校验、预算控制和安全边界。")

    assert not service._has_lexical_support("volatile 是否能保证 count++ 的线程安全？", [evidence])


def test_answer_service_expands_rrf_retrieval_aliases() -> None:
    service = AnswerService(
        cast(Any, None),
        cast(Any, None),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
    )
    evidence = chunk()
    evidence = replace(
        evidence,
        content="Reciprocal Rank Fusion combines lexical and vector retrieval rankings.",
    )

    assert service._has_lexical_support("全文检索和向量检索为什么需要 RRF 融合？", [evidence])

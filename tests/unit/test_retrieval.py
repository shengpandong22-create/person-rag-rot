from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from agent_mentor.api.errors import AppError
from agent_mentor.application.answer_service import AnswerService, ensure_citations_are_valid
from agent_mentor.domain.evidence import EvidenceGatePolicy
from agent_mentor.infrastructure.retriever import (
    AdjacentFilterStrategy,
    CandidateExpansionStrategy,
    PostgresHybridRetriever,
    RetrievalExperimentMode,
    RetrievalFilterReason,
    _Candidate,
    _infer_retrieved_block_type,
    _lexical_overlap,
    _lexical_terms,
    _merge_query_variant_candidates,
    _rerank_score,
    _retrieval_explanation,
)
from agent_mentor.ports.knowledge_retriever import RetrievalQuery, RetrievedChunk
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


def test_eval_multi_query_merge_keeps_fixed_candidate_budget() -> None:
    document = SimpleNamespace(id=uuid4())
    shared = SimpleNamespace(id=uuid4())
    first_only = SimpleNamespace(id=uuid4())
    second_only = SimpleNamespace(id=uuid4())
    first = [
        _Candidate(cast(Any, shared), cast(Any, document), 1, 0.9),
        _Candidate(cast(Any, first_only), cast(Any, document), 2, 0.8),
    ]
    second = [
        _Candidate(cast(Any, shared), cast(Any, document), 1, 0.7),
        _Candidate(cast(Any, second_only), cast(Any, document), 2, 0.6),
    ]

    merged = _merge_query_variant_candidates([first, second], candidate_k=2)

    assert len(merged) == 2
    assert merged[0].chunk.id == shared.id
    assert [item.rank for item in merged] == [1, 2]


def test_eval_experiment_default_is_current_heuristic_rerank() -> None:
    import inspect

    parameter = inspect.signature(PostgresHybridRetriever.retrieve).parameters["experiment_mode"]

    assert parameter.default is RetrievalExperimentMode.RRF_HEURISTIC


@pytest.mark.asyncio
async def test_default_retrieval_path_equals_explicit_current_heuristic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Sessions:
        def __call__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return object()

        async def __aexit__(self, *args):  # type: ignore[no-untyped-def]
            return None

    document = SimpleNamespace(
        id=uuid4(),
        title="RAG Guide",
        logical_name="rag-guide",
        source_url=None,
        trust_level="curated",
    )
    first = SimpleNamespace(
        id=uuid4(),
        content="RAG evidence",
        heading_path=["RAG"],
        page_number=None,
        chunk_index=0,
    )
    second = SimpleNamespace(
        id=uuid4(),
        content="retrieval ranking",
        heading_path=["Retrieval"],
        page_number=None,
        chunk_index=2,
    )
    vector = [
        _Candidate(cast(Any, first), cast(Any, document), 1, 0.8),
        _Candidate(cast(Any, second), cast(Any, document), 2, 0.7),
    ]
    text = [
        _Candidate(cast(Any, second), cast(Any, document), 1, 2.0),
        _Candidate(cast(Any, first), cast(Any, document), 2, 1.0),
    ]
    retriever = PostgresHybridRetriever(
        cast(Any, Sessions()), cast(Any, None), max_chunks_per_document=3
    )
    monkeypatch.setattr(retriever, "_vector_candidates", AsyncMock(return_value=vector))
    monkeypatch.setattr(retriever, "_text_candidates", AsyncMock(return_value=text))
    query = RetrievalQuery(uuid4(), "RAG retrieval", top_k=2, candidate_k=2)

    default = await retriever.retrieve(query)
    explicit = await retriever.retrieve(
        query, experiment_mode=RetrievalExperimentMode.RRF_HEURISTIC
    )

    assert default == explicit


@pytest.mark.asyncio
async def test_diagnostics_share_pipeline_and_attribute_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Sessions:
        def __call__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return object()

        async def __aexit__(self, *args):  # type: ignore[no-untyped-def]
            return None

    document = SimpleNamespace(
        id=uuid4(),
        title="Guide",
        logical_name="guide",
        source_url=None,
        trust_level="curated",
    )
    candidates = []
    for index, score in enumerate((0.9, 0.8, 0.7, 0.6)):
        model = SimpleNamespace(
            id=uuid4(),
            content=f"evidence {index}",
            heading_path=["Guide"],
            page_number=None,
            chunk_index=index,
        )
        candidates.append(_Candidate(cast(Any, model), cast(Any, document), index + 1, score))
    retriever = PostgresHybridRetriever(
        cast(Any, Sessions()), cast(Any, None), max_chunks_per_document=2
    )
    monkeypatch.setattr(retriever, "_vector_candidates", AsyncMock(return_value=candidates))
    query = RetrievalQuery(uuid4(), "evidence", top_k=1, candidate_k=4)

    diagnostics = await retriever.retrieve_with_diagnostics(
        query, experiment_mode=RetrievalExperimentMode.VECTOR_ONLY
    )
    production = await retriever.retrieve(
        query, experiment_mode=RetrievalExperimentMode.VECTOR_ONLY
    )

    assert list(diagnostics.final_results) == production
    assert [item.chunk_index for item in diagnostics.post_filter_candidates] == [0, 2]
    assert [item.reason for item in diagnostics.filtered_out] == [
        RetrievalFilterReason.ADJACENT_CHUNK,
        RetrievalFilterReason.PER_DOCUMENT_LIMIT,
        RetrievalFilterReason.TOP_K_CUTOFF,
    ]


@pytest.mark.asyncio
async def test_eval_can_disable_per_document_limit_without_changing_other_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Sessions:
        def __call__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return object()

        async def __aexit__(self, *args):  # type: ignore[no-untyped-def]
            return None

    document = SimpleNamespace(
        id=uuid4(), title="Guide", logical_name="guide", source_url=None, trust_level="curated"
    )
    candidates = []
    for index in range(5):
        model = SimpleNamespace(
            id=uuid4(),
            content=f"evidence {index}",
            heading_path=["Guide"],
            page_number=None,
            chunk_index=index,
        )
        candidates.append(
            _Candidate(cast(Any, model), cast(Any, document), index + 1, 1 - index / 10)
        )
    query = RetrievalQuery(uuid4(), "evidence", top_k=5, candidate_k=5)

    limited = PostgresHybridRetriever(
        cast(Any, Sessions()), cast(Any, None), max_chunks_per_document=2
    )
    unlimited = PostgresHybridRetriever(
        cast(Any, Sessions()), cast(Any, None), max_chunks_per_document=None
    )
    monkeypatch.setattr(limited, "_vector_candidates", AsyncMock(return_value=candidates))
    monkeypatch.setattr(unlimited, "_vector_candidates", AsyncMock(return_value=candidates))

    limited_result = await limited.retrieve_with_diagnostics(
        query, experiment_mode=RetrievalExperimentMode.VECTOR_ONLY
    )
    unlimited_result = await unlimited.retrieve_with_diagnostics(
        query, experiment_mode=RetrievalExperimentMode.VECTOR_ONLY
    )

    assert [item.chunk_index for item in limited_result.final_results] == [0, 2]
    assert [item.chunk_index for item in unlimited_result.final_results] == [0, 2, 4]


@pytest.mark.asyncio
async def test_eval_same_heading_filter_keeps_adjacent_cross_heading_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Sessions:
        def __call__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return object()

        async def __aexit__(self, *args):  # type: ignore[no-untyped-def]
            return None

    document = SimpleNamespace(
        id=uuid4(), title="Guide", logical_name="guide", source_url=None, trust_level="curated"
    )
    candidates = [
        _Candidate(
            cast(
                Any,
                SimpleNamespace(
                    id=uuid4(),
                    content="first",
                    heading_path=["A"],
                    page_number=None,
                    chunk_index=0,
                ),
            ),
            cast(Any, document),
            1,
            0.9,
        ),
        _Candidate(
            cast(
                Any,
                SimpleNamespace(
                    id=uuid4(),
                    content="second",
                    heading_path=["B"],
                    page_number=None,
                    chunk_index=1,
                ),
            ),
            cast(Any, document),
            2,
            0.8,
        ),
    ]
    retriever = PostgresHybridRetriever(
        cast(Any, Sessions()), cast(Any, None), max_chunks_per_document=3
    )
    monkeypatch.setattr(retriever, "_vector_candidates", AsyncMock(return_value=candidates))
    query = RetrievalQuery(uuid4(), "evidence", top_k=2, candidate_k=2)

    current = await retriever.retrieve_with_diagnostics(
        query,
        experiment_mode=RetrievalExperimentMode.VECTOR_ONLY,
    )
    heading_aware = await retriever.retrieve_with_diagnostics(
        query,
        experiment_mode=RetrievalExperimentMode.VECTOR_ONLY,
        adjacent_filter_strategy=AdjacentFilterStrategy.SAME_HEADING,
    )

    assert [item.chunk_index for item in current.final_results] == [0]
    assert [item.chunk_index for item in heading_aware.final_results] == [0, 1]


@pytest.mark.asyncio
async def test_eval_heading_expansion_merges_into_fixed_candidate_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Sessions:
        def __call__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return object()

        async def __aexit__(self, *args):  # type: ignore[no-untyped-def]
            return None

    document = SimpleNamespace(
        id=uuid4(), title="Guide", logical_name="guide", source_url=None, trust_level="curated"
    )

    def candidate(index: int, content: str) -> _Candidate:
        model = SimpleNamespace(
            id=uuid4(),
            content=content,
            heading_path=[content],
            page_number=None,
            chunk_index=index * 2,
        )
        return _Candidate(cast(Any, model), cast(Any, document), index + 1, 0.9 - index / 10)

    vector = [candidate(0, "vector"), candidate(1, "shared")]
    heading = [vector[1], candidate(2, "heading")]
    retriever = PostgresHybridRetriever(
        cast(Any, Sessions()), cast(Any, None), max_chunks_per_document=3
    )
    monkeypatch.setattr(retriever, "_vector_candidates", AsyncMock(return_value=vector))
    monkeypatch.setattr(retriever, "_heading_candidates", AsyncMock(return_value=heading))
    query = RetrievalQuery(uuid4(), "evidence", top_k=2, candidate_k=2)

    diagnostics = await retriever.retrieve_with_diagnostics(
        query,
        experiment_mode=RetrievalExperimentMode.VECTOR_ONLY,
        candidate_expansion=CandidateExpansionStrategy.HEADING_LEXICAL,
    )

    assert len(diagnostics.ordered_candidates) == 2
    assert diagnostics.ordered_candidates[0].content == "shared"
    assert [item.content for item in diagnostics.heading_candidates] == ["shared"]


@pytest.mark.asyncio
async def test_eval_heading_shadow_never_changes_primary_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Sessions:
        def __call__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return object()

        async def __aexit__(self, *args):  # type: ignore[no-untyped-def]
            return None

    document = SimpleNamespace(
        id=uuid4(), title="Guide", logical_name="guide", source_url=None, trust_level="curated"
    )

    def candidate(index: int, content: str) -> _Candidate:
        model = SimpleNamespace(
            id=uuid4(),
            content=content,
            heading_path=[content],
            page_number=None,
            chunk_index=index * 2,
        )
        return _Candidate(cast(Any, model), cast(Any, document), index + 1, 0.9 - index / 10)

    vector = [candidate(0, "vector-1"), candidate(1, "vector-2")]
    heading_only = candidate(2, "heading-only")
    heading = [vector[1], heading_only]
    retriever = PostgresHybridRetriever(
        cast(Any, Sessions()), cast(Any, None), max_chunks_per_document=3
    )
    monkeypatch.setattr(retriever, "_vector_candidates", AsyncMock(return_value=vector))
    monkeypatch.setattr(retriever, "_heading_candidates", AsyncMock(return_value=heading))
    query = RetrievalQuery(uuid4(), "evidence", top_k=2, candidate_k=2)

    baseline = await retriever.retrieve_with_diagnostics(
        query,
        experiment_mode=RetrievalExperimentMode.VECTOR_ONLY,
    )
    shadow = await retriever.retrieve_with_diagnostics(
        query,
        experiment_mode=RetrievalExperimentMode.VECTOR_ONLY,
        candidate_expansion=CandidateExpansionStrategy.HEADING_SHADOW,
    )

    assert shadow.final_results == baseline.final_results
    assert shadow.ordered_candidates == baseline.ordered_candidates
    assert [item.content for item in shadow.supplemental_candidates] == ["heading-only"]
    assert shadow.supplemental_candidates[0].heading_rank == heading_only.rank
    assert shadow.supplemental_candidates[0].heading_score == heading_only.score


@pytest.mark.asyncio
async def test_eval_heading_shadow_deduplicates_only_actual_primary_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Sessions:
        def __call__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return object()

        async def __aexit__(self, *args):  # type: ignore[no-untyped-def]
            return None

    document = SimpleNamespace(
        id=uuid4(), title="Guide", logical_name="guide", source_url=None, trust_level="curated"
    )

    def candidate(index: int, content: str) -> _Candidate:
        model = SimpleNamespace(
            id=uuid4(),
            content=content,
            heading_path=[content],
            page_number=None,
            chunk_index=index * 2,
        )
        return _Candidate(cast(Any, model), cast(Any, document), index + 1, 0.9 - index / 10)

    primary = candidate(0, "primary")
    vector_tail = candidate(1, "vector-tail-heading-hit")
    heading_only = candidate(2, "heading-only")
    retriever = PostgresHybridRetriever(
        cast(Any, Sessions()), cast(Any, None), max_chunks_per_document=3
    )
    monkeypatch.setattr(
        retriever,
        "_vector_candidates",
        AsyncMock(return_value=[primary, vector_tail]),
    )
    monkeypatch.setattr(
        retriever,
        "_heading_candidates",
        AsyncMock(return_value=[primary, vector_tail, heading_only]),
    )
    query = RetrievalQuery(uuid4(), "evidence", top_k=1, candidate_k=3)

    diagnostics = await retriever.retrieve_with_diagnostics(
        query,
        experiment_mode=RetrievalExperimentMode.VECTOR_ONLY,
        candidate_expansion=CandidateExpansionStrategy.HEADING_SHADOW,
    )

    assert [item.content for item in diagnostics.final_results] == ["primary"]
    assert [item.content for item in diagnostics.supplemental_candidates] == [
        "vector-tail-heading-hit",
        "heading-only",
    ]


@pytest.mark.asyncio
async def test_eval_semantic_query_shadow_is_monotonic_and_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Sessions:
        def __call__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return object()

        async def __aexit__(self, *args):  # type: ignore[no-untyped-def]
            return None

    document = SimpleNamespace(
        id=uuid4(), title="Guide", logical_name="guide", source_url=None, trust_level="curated"
    )

    def candidate(index: int, content: str) -> _Candidate:
        model = SimpleNamespace(
            id=uuid4(),
            content=content,
            heading_path=[content],
            page_number=None,
            chunk_index=index * 2,
        )
        return _Candidate(cast(Any, model), cast(Any, document), index + 1, 0.9 - index / 10)

    primary = [candidate(0, "primary-1"), candidate(1, "shared")]
    semantic_only = candidate(2, "semantic-only")
    vector_mock = AsyncMock(side_effect=[primary, [primary[1], semantic_only]])
    retriever = PostgresHybridRetriever(
        cast(Any, Sessions()), cast(Any, None), max_chunks_per_document=3
    )
    monkeypatch.setattr(retriever, "_vector_candidates", vector_mock)
    query = RetrievalQuery(uuid4(), "低词面改写", top_k=2, candidate_k=2)

    shadow = await retriever.retrieve_with_diagnostics(
        query,
        experiment_mode=RetrievalExperimentMode.VECTOR_ONLY,
        candidate_expansion=CandidateExpansionStrategy.SEMANTIC_QUERY_SHADOW,
    )

    assert [item.content for item in shadow.final_results] == ["primary-1", "shared"]
    assert [item.content for item in shadow.ordered_candidates] == ["primary-1", "shared"]
    assert [item.content for item in shadow.supplemental_candidates] == ["semantic-only"]
    assert shadow.supplemental_candidates[0].semantic_rank == semantic_only.rank
    assert vector_mock.await_args_list[0].args[2] == "低词面改写"
    assert vector_mock.await_args_list[1].args[2] == (
        "为这个句子生成表示以用于检索相关文章：低词面改写"
    )


def test_retrieval_explanation_contains_rank_signals() -> None:
    explanation = _retrieval_explanation(
        fused_score=0.0325,
        rerank_score=0.0395,
        lexical_overlap=0.5,
        vector_rank=1,
        text_rank=3,
        vector_score=0.8123,
        text_score=0.4567,
    )

    assert "RRF=0.0325" in explanation
    assert "rerank=0.0395" in explanation
    assert "lexical_overlap=0.50" in explanation
    assert "vector_rank=1" in explanation
    assert "text_rank=3" in explanation
    assert _infer_retrieved_block_type("| A | B |\n| - | - |\n| x | y |") == "table"


def test_postgres_retriever_filters_inactive_chunks() -> None:
    retriever = PostgresHybridRetriever.__new__(PostgresHybridRetriever)
    query = SimpleNamespace(knowledge_base_id=uuid4(), trust_levels=())

    compiled = str(
        retriever._base_query(cast(Any, query)).compile(  # pyright: ignore[reportPrivateUsage]
            compile_kwargs={"literal_binds": False}
        )
    ).lower()

    assert "knowledge_chunks.is_active" in compiled


def test_chinese_lexical_terms_include_bigrams_for_plugin_free_search() -> None:
    terms = _lexical_terms("引用白名单如何判断证据不足")

    assert "引用" in terms
    assert "白名" in terms
    assert "证据" in terms


def test_rerank_score_uses_lexical_and_raw_retrieval_signals() -> None:
    base = _rerank_score(
        normalized="引用白名单 证据不足",
        content="完全无关内容",
        fused_score=0.02,
        vector_score=0.2,
        text_score=0,
    )
    boosted = _rerank_score(
        normalized="引用白名单 证据不足",
        content="引用白名单用于判断证据不足时是否显式降级。",
        fused_score=0.02,
        vector_score=0.8,
        text_score=4,
    )

    assert _lexical_overlap("引用白名单 证据不足", "引用白名单用于判断证据不足") > 0
    assert boosted > base


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


def test_answer_service_rejects_external_constraint_with_only_generic_project_overlap() -> None:
    service = AnswerService(
        cast(Any, None),
        cast(Any, None),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
    )
    evidence = replace(
        chunk(),
        content="RAG 系统设计需要通过证据门禁、引用白名单和检索诊断降低幻觉。",
    )

    assert not service._has_lexical_support(
        "唐朝开元年间的具体盐税制度如何影响 RAG 系统设计？", [evidence]
    )


def test_answer_service_assesses_only_lexically_supported_candidates() -> None:
    service = AnswerService(
        cast(Any, None),
        cast(Any, None),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.02,
    )
    unrelated_high_score = replace(
        chunk(),
        content="唐朝开元年间盐税制度主要涉及财政结构和区域治理。",
        score=0.99,
    )
    supported_low_score = replace(
        chunk(),
        content="RAG 系统通过证据门禁和引用白名单降低幻觉，但仍需检索质量兜底。",
        score=0.01,
    )

    supported, sufficient = service.assess_evidence(
        "RAG 系统如何通过引用白名单降低幻觉？",
        [unrelated_high_score, supported_low_score],
    )

    assert supported == [supported_low_score]
    assert sufficient is False


def test_evidence_diagnostics_preserve_current_binary_decision() -> None:
    service = AnswerService(
        cast(Any, None),
        cast(Any, None),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.02,
    )
    supported = replace(
        chunk(),
        content="RAG 使用 evidence gate 和 citation 白名单。",
        score=0.03,
    )
    unrelated = replace(
        chunk(),
        chunk_id=uuid4(),
        document_title="历史资料",
        heading_path=("财政",),
        content="唐朝盐税制度。",
        score=0.99,
    )

    assessment = service.assess_evidence_diagnostics(
        "RAG 的 evidence gate 如何约束 citation？", [unrelated, supported]
    )
    candidates, sufficient = service.assess_evidence(
        "RAG 的 evidence gate 如何约束 citation？", [unrelated, supported]
    )

    assert candidates == [supported]
    assert sufficient is assessment.production_sufficient is True
    assert assessment.decision.value == "full"
    assert assessment.supported_chunk_ids == (str(supported.chunk_id),)
    assert assessment.top_supported_score == 0.03
    assert assessment.coverage_ratio > 0
    assert assessment.candidate_assessments[0].lexical_support is False
    assert assessment.candidate_assessments[1].lexical_support is True


def test_evidence_diagnostics_record_uncovered_numeric_demand_without_changing_gate() -> None:
    service = AnswerService(
        cast(Any, None),
        cast(Any, None),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
    )
    evidence = replace(
        chunk(),
        content="checkpoint 可以保存流程轨迹并恢复业务状态。",
        score=0.5,
    )

    assessment = service.assess_evidence_diagnostics(
        "checkpoint 如何恢复，是否保证 30 秒 RTO？", [evidence]
    )

    assert assessment.production_sufficient is True
    assert assessment.numeric_tokens_requested == ("30",)
    assert assessment.numeric_tokens_covered == ()
    assert "保证" in assessment.demand_markers
    assert {item.demand_type for item in assessment.demand_assessments} == {
        "exact_value",
        "guarantee",
    }
    assert all(not item.matched for item in assessment.demand_assessments)


def test_evidence_diagnostics_record_clause_level_support() -> None:
    service = AnswerService(
        cast(Any, None),
        cast(Any, None),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
    )
    evidence = replace(
        chunk(),
        content="checkpoint 保存流程轨迹并恢复业务状态。",
        score=0.5,
    )

    assessment = service.assess_evidence_diagnostics(
        "checkpoint 如何恢复，未来版本何时提供分布式任务租约？", [evidence]
    )

    assert len(assessment.clause_assessments) == 2
    assert assessment.clause_assessments[0].lexical_support is True
    assert assessment.clause_assessments[1].lexical_support is False
    assert {item.demand_type for item in assessment.demand_assessments} == {
        "date",
        "future_version",
    }
    assert [item.status.value for item in assessment.claim_assessments] == [
        "supported",
        "unknown",
    ]
    assert assessment.claim_decision.value == "partial"


def test_claim_diagnostics_mark_unmet_exact_value_as_unsupported() -> None:
    service = AnswerService(
        cast(Any, None),
        cast(Any, None),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
    )
    evidence = replace(
        chunk(),
        content="系统使用 HNSW 索引，ef_search 是检索参数。",
        score=0.5,
    )

    assessment = service.assess_evidence_diagnostics("HNSW ef_search 多少？", [evidence])

    claim = assessment.claim_assessments[0]
    assert claim.requirement_types == ("exact_value",)
    assert claim.status.value == "unsupported"
    assert claim.reasons == ("unmet_exact_value_demand",)
    assert claim.evidence_chunk_ids == (str(evidence.chunk_id),)
    assert assessment.claim_decision.value == "none"


def test_clause_demand_policy_rejects_partial_evidence_when_explicitly_enabled() -> None:
    evidence = replace(
        chunk(),
        content="checkpoint 保存流程轨迹并恢复业务状态。",
        score=0.5,
    )
    current = AnswerService(
        cast(Any, None),
        cast(Any, None),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
    )
    candidate = AnswerService(
        cast(Any, None),
        cast(Any, None),
        default_top_k=6,
        default_candidate_k=20,
        min_evidence_score=0.01,
        evidence_gate_policy=EvidenceGatePolicy.CLAUSE_DEMAND_V1,
    )
    question = "checkpoint 如何恢复，未来版本何时提供分布式任务租约？"

    _, current_sufficient = current.assess_evidence(question, [evidence])
    supported, candidate_sufficient = candidate.assess_evidence(question, [evidence])
    assessment = candidate.assess_evidence_diagnostics(question, [evidence])

    assert current_sufficient is True
    assert supported == [evidence]
    assert candidate_sufficient is False
    assert assessment.decision.value == "partial"
    assert assessment.rejection_reasons == (
        "uncovered_question_clause",
        "unmet_explicit_demand",
    )


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

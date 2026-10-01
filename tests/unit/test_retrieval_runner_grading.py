from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from agent_mentor.ports.knowledge_retriever import RetrievedChunk
from evals.runners.retrieval_runner import (
    SupplementalConsumptionStrategy,
    _failure_category,
    _first_relevant_rank,
    _first_relevant_rank_by_id,
    _freeze_manifest_sha256,
    _heading_matches,
    _is_graded,
    _select_supplemental_candidates,
    _source_heading_matches,
    _supplemental_recall_metrics,
)
from evals.schema import Answerability, LabelOrigin, RelevantSource, RetrievalEvalCase


def _chunk(chunk_id=None) -> RetrievedChunk:  # type: ignore[no-untyped-def]
    return RetrievedChunk(
        chunk_id=chunk_id or uuid4(),
        document_id=uuid4(),
        document_title="第 3 课：混合检索与可信 RAG 回答",
        source_url=None,
        trust_level="curated",
        heading_path=("检索", "证据门禁"),
        page_number=None,
        block_type="paragraph",
        chunk_index=0,
        content="证据门禁通过排序分与证据信号分离来避免误判。",
        score=0.03,
        retrieval_explanation="RRF=0.0300",
    )


def test_supplemental_recall_preserves_primary_and_measures_incremental_gain() -> None:
    metrics = _supplemental_recall_metrics(
        [
            (5, None, 3),
            (None, 2, 4),
            (None, 8, 10),
            (None, None, 2),
        ]
    )

    assert metrics["primary_at_6_plus_supplemental_at_1"] == 0.25
    assert metrics["primary_at_6_plus_supplemental_at_3"] == 0.5
    assert metrics["primary_at_6_plus_supplemental_at_6"] == 0.5
    assert metrics["primary_at_6_plus_supplemental_at_20"] == 0.75
    assert metrics["average_supplemental_candidate_count"] == 4.75


def test_supplemental_consumption_is_fixed_or_evidence_gated() -> None:
    candidates = [_chunk(), _chunk()]

    fixed = _select_supplemental_candidates(
        candidates,
        strategy=SupplementalConsumptionStrategy.FIXED,
        supplemental_k=1,
        primary_evidence_sufficient=True,
    )
    skipped = _select_supplemental_candidates(
        candidates,
        strategy=SupplementalConsumptionStrategy.EVIDENCE_GATED,
        supplemental_k=1,
        primary_evidence_sufficient=True,
    )
    triggered = _select_supplemental_candidates(
        candidates,
        strategy=SupplementalConsumptionStrategy.EVIDENCE_GATED,
        supplemental_k=1,
        primary_evidence_sufficient=False,
    )

    assert fixed == candidates[:1]
    assert skipped == []
    assert triggered == candidates[:1]


def test_retrieval_disagreement_consumes_only_strong_heading_with_small_vector_gap() -> None:
    candidates = [replace(_chunk(), heading_score=2.0)]
    uncertain_vector = [
        replace(_chunk(), vector_score=0.60),
        replace(_chunk(), vector_score=0.57),
    ]
    confident_vector = [
        replace(_chunk(), vector_score=0.70),
        replace(_chunk(), vector_score=0.60),
    ]

    triggered = _select_supplemental_candidates(
        candidates,
        strategy=SupplementalConsumptionStrategy.RETRIEVAL_DISAGREEMENT,
        supplemental_k=7,
        primary_evidence_sufficient=True,
        vector_candidates=uncertain_vector,
    )
    skipped = _select_supplemental_candidates(
        candidates,
        strategy=SupplementalConsumptionStrategy.RETRIEVAL_DISAGREEMENT,
        supplemental_k=7,
        primary_evidence_sufficient=False,
        vector_candidates=confident_vector,
    )

    assert triggered == candidates
    assert skipped == []


def test_quota4_acceptance_report_records_its_own_freeze_manifest() -> None:
    dataset = Path("evals/datasets/retrieval_quota4_acceptance_v1.jsonl")

    assert _freeze_manifest_sha256(dataset) is not None


def test_same_heading_acceptance_report_records_its_own_freeze_manifest() -> None:
    dataset = Path("evals/datasets/retrieval_same_heading_acceptance_v1.jsonl")

    assert _freeze_manifest_sha256(dataset) is not None


def test_trigger_development_report_records_its_own_freeze_manifest() -> None:
    dataset = Path("evals/datasets/retrieval_trigger_development_v1.jsonl")

    assert _freeze_manifest_sha256(dataset) is not None


def test_heading_matches_is_a_contiguous_subsequence() -> None:
    actual = ("第 3 课", "检索", "证据门禁", "实现")

    assert _heading_matches((), actual) is True
    assert _heading_matches(("检索", "证据门禁"), actual) is True
    # An outer chapter being inserted must not break the label.
    assert _heading_matches(("检索", "证据门禁"), ("新增章", *actual)) is True
    # Out-of-order or gapped paths must not match.
    assert _heading_matches(("证据门禁", "检索"), actual) is False
    assert _heading_matches(("检索", "实现"), actual) is False
    assert _heading_matches(("检索", "证据门禁", "实现", "更多"), actual) is False
    assert _heading_matches(("检索",), ()) is False


def test_heading_matches_tolerates_whitespace_differences() -> None:
    assert _heading_matches(("证据门禁",), ("检索", " 证据门禁 ")) is True


def test_source_heading_matches_parser_full_path_with_document_title() -> None:
    assert (
        _source_heading_matches(
            ("第 3 课", "检索", "证据门禁"),
            ("检索", "证据门禁"),
            "第 3 课",
        )
        is True
    )


def test_first_relevant_rank_by_id_uses_human_labels_not_keywords() -> None:
    irrelevant = _chunk()
    target = _chunk()
    chunks = [irrelevant, target]

    assert _first_relevant_rank_by_id(chunks, (target.chunk_id,)) == 2
    assert _first_relevant_rank_by_id(chunks, (uuid4(),)) is None


def test_keyword_rank_remains_available_as_a_diagnostic() -> None:
    chunks = [_chunk()]

    assert _first_relevant_rank(chunks, ("证据门禁",)) == 1
    assert _first_relevant_rank(chunks, ("完全不存在的词",)) is None


def test_negative_row_is_graded_because_its_label_is_the_reason() -> None:
    from evals.schema import NegativeReason

    case = RetrievalEvalCase(
        "n1",
        "q",
        Answerability.NONE,
        (),
        (),
        negative_reason=NegativeReason.FALSE_PREMISE,
    )

    assert _is_graded(case) is True


def test_labelled_positive_row_is_graded() -> None:
    case = RetrievalEvalCase(
        "p1",
        "q",
        Answerability.FULL,
        (RelevantSource("doc.md"),),
        (),
    )

    assert _is_graded(case) is True


def test_unlabelled_positive_row_is_not_graded_even_in_human_origin() -> None:
    case = RetrievalEvalCase("p2", "q", Answerability.FULL, (), ())

    assert case.label_origin is LabelOrigin.HUMAN
    assert _is_graded(case) is False


def test_legacy_ungraded_row_is_never_graded() -> None:
    case = RetrievalEvalCase(
        "p3",
        "q",
        Answerability.FULL,
        (RelevantSource("doc.md"),),
        (),
        label_origin=LabelOrigin.LEGACY_UNGRADED,
    )

    assert _is_graded(case) is False


def test_failure_attribution_distinguishes_candidate_ranking_and_filters() -> None:
    case = RetrievalEvalCase(
        "p4",
        "q",
        Answerability.FULL,
        (RelevantSource("doc.md"),),
        (),
    )
    common = {
        "case": case,
        "ground_truth_mode": "resolved",
        "evidence_sufficient": False,
        "top_k": 6,
    }

    assert (
        _failure_category(
            **common,
            first_rank=None,
            first_raw_candidate_rank=None,
            first_post_filter_rank=None,
            relevant_filter_reasons=[],
        )
        == "candidate_recall_miss"
    )
    assert (
        _failure_category(
            **common,
            first_rank=None,
            first_raw_candidate_rank=4,
            first_post_filter_rank=8,
            relevant_filter_reasons=[],
        )
        == "ranking_cutoff_miss"
    )
    assert (
        _failure_category(
            **common,
            first_rank=None,
            first_raw_candidate_rank=3,
            first_post_filter_rank=None,
            relevant_filter_reasons=["adjacent_chunk"],
        )
        == "adjacent_filter_miss"
    )

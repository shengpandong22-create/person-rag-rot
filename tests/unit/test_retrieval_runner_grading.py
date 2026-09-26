from __future__ import annotations

from uuid import uuid4

from agent_mentor.ports.knowledge_retriever import RetrievedChunk
from evals.runners.retrieval_runner import (
    _first_relevant_rank,
    _first_relevant_rank_by_id,
    _heading_matches,
    _is_graded,
    _source_heading_matches,
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

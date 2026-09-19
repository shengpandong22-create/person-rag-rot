from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.schema import (
    Answerability,
    LabelOrigin,
    NegativeReason,
    RetrievalEvalCase,
    parse_case,
)


def _row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "ret-999",
        "question": "为什么需要分离排序分与证据置信度？",
        "answerability": "full",
        "split": "validation",
        "relevant_sources": [
            {
                "document_logical_name": "第 3 课：混合检索与可信 RAG 回答",
                "heading_path": ["检索", "证据门禁"],
                "required_answer_points": ["排序分是相对信号", "绝对阈值需要独立信号"],
            }
        ],
        "diagnostic_keywords": ["排序", "证据"],
    }
    base.update(overrides)
    return base


def test_parses_full_answerability_case_with_stable_locations() -> None:
    case = parse_case(_row(), line_number=1)

    assert case.answerability is Answerability.FULL
    assert case.answerable is True
    assert case.relevant_sources[0].document_logical_name == "第 3 课：混合检索与可信 RAG 回答"
    assert case.relevant_sources[0].heading_path == ("检索", "证据门禁")
    assert case.relevant_sources[0].required_answer_points[1] == "绝对阈值需要独立信号"
    assert case.diagnostic_keywords == ("排序", "证据")
    assert case.label_origin is LabelOrigin.HUMAN


def test_partial_answerability_still_counts_as_answerable() -> None:
    case = parse_case(
        _row(
            answerability="partial",
            negative_reason="partial_evidence_only",
            negative_note="只能回答解析限制，OCR 能力无资料。",
        ),
        line_number=1,
    )

    assert case.answerability is Answerability.PARTIAL
    assert case.answerable is True
    assert case.negative_reason is NegativeReason.PARTIAL_EVIDENCE_ONLY


def test_partial_without_negative_reason_is_rejected_as_underspecified() -> None:
    with pytest.raises(ValueError, match="answerability=partial requires negative_reason"):
        parse_case(_row(answerability="partial"), line_number=1)


def test_negative_case_requires_reason_and_forbids_relevant_sources() -> None:
    with pytest.raises(ValueError, match="negative_reason"):
        parse_case(
            _row(
                answerability="none",
                relevant_sources=[],
                diagnostic_keywords=[],
            ),
            line_number=1,
        )

    with pytest.raises(ValueError, match="must not declare relevant_sources"):
        parse_case(
            _row(
                answerability="none",
                negative_reason="false_premise",
                diagnostic_keywords=[],
            ),
            line_number=1,
        )


def test_negative_case_with_reason_is_accepted() -> None:
    case = parse_case(
        _row(
            id="ret-neg-1",
            answerability="none",
            relevant_sources=[],
            diagnostic_keywords=[],
            negative_reason="false_premise",
            negative_note="问题预设了项目并未采用的 Elasticsearch 主检索架构。",
        ),
        line_number=1,
    )

    assert case.answerability is Answerability.NONE
    assert case.answerable is False
    assert case.negative_reason is NegativeReason.FALSE_PREMISE
    assert case.negative_note is not None


def test_answerable_case_without_relevant_sources_is_rejected() -> None:
    with pytest.raises(ValueError, match="requires at least one relevant_sources"):
        parse_case(_row(relevant_sources=[]), line_number=1)


def test_unknown_answerability_value_is_rejected() -> None:
    with pytest.raises(ValueError, match="answerability must be one of"):
        parse_case(_row(answerability="mostly"), line_number=1)


def test_unknown_negative_reason_is_rejected_with_valid_values() -> None:
    with pytest.raises(ValueError, match="unknown negative_reason"):
        parse_case(
            _row(answerability="none", relevant_sources=[], negative_reason="not_a_reason"),
            line_number=1,
        )


def test_legacy_answerable_boolean_is_bridged_but_keeps_human_origin() -> None:
    case = parse_case(
        {
            "id": "legacy-1",
            "question": "旧的二值样本",
            "answerable": True,
            "expected_keywords": ["RAG"],
            "relevant_sources": [{"document_logical_name": "第 1 课"}],
        },
        line_number=1,
    )

    assert case.answerability is Answerability.FULL


def test_legacy_boolean_without_sources_fails_instead_of_silently_passing() -> None:
    with pytest.raises(ValueError, match="requires at least one relevant_sources"):
        parse_case(
            {"id": "legacy-2", "question": "旧的二值样本", "answerable": True},
            line_number=1,
        )


def test_to_json_round_trips_through_parse_case() -> None:
    case = RetrievalEvalCase(
        case_id="ret-rt",
        question="round trip?",
        answerability=Answerability.FULL,
        relevant_sources=parse_case(_row(), line_number=1).relevant_sources,
        diagnostic_keywords=("a",),
        split="holdout",
        tags=("negative_adjacent",),
    )

    restored = parse_case(json.loads(json.dumps(case.to_json())), line_number=1)

    assert restored.case_id == case.case_id
    assert restored.answerability is case.answerability
    assert restored.relevant_sources == case.relevant_sources
    assert restored.split == "holdout"
    assert restored.tags == ("negative_adjacent",)


def test_dataset_with_duplicate_ids_is_rejected(tmp_path: Path) -> None:
    from evals.schema import load_dataset

    dataset = tmp_path / "dup.jsonl"
    dataset.write_text(
        "\n".join(
            [
                json.dumps(_row()),
                json.dumps(_row()),
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate ids"):
        load_dataset(dataset)


def test_migration_mode_accepts_unlabeled_positive_but_downgrades_origin() -> None:
    case = parse_case(_row(relevant_sources=[], tags=[]), line_number=1, require_graded=False)

    assert case.label_origin is LabelOrigin.LEGACY_UNGRADED
    assert "needs_grading" in case.tags
    assert case.relevant_sources == ()


def test_strict_mode_rejects_unlabeled_positive_so_it_cannot_be_scored() -> None:
    with pytest.raises(ValueError, match="requires at least one relevant_sources"):
        parse_case(_row(relevant_sources=[]), line_number=1, require_graded=True)


def test_migration_mode_still_rejects_negative_without_reason() -> None:
    with pytest.raises(ValueError, match="negative_reason"):
        parse_case(
            _row(answerability="none", relevant_sources=[], tags=[]),
            line_number=1,
            require_graded=False,
        )


def test_load_legacy_case_is_marked_ungraded_and_keeps_negative_reason() -> None:
    from evals.schema import DIAGNOSTIC_ONLY_NOTE, load_legacy_case

    positive = load_legacy_case(
        {
            "id": "ret-001",
            "question": "RAG 为什么能降低幻觉？",
            "expected_keywords": ["RAG", "证据"],
            "answerable": True,
        },
        line_number=1,
    )
    assert positive.label_origin is LabelOrigin.LEGACY_UNGRADED
    assert DIAGNOSTIC_ONLY_NOTE in positive.tags
    assert positive.relevant_sources == ()

    negative = load_legacy_case(
        {
            "id": "ret-027",
            "question": "唐朝开元年间的盐税制度如何影响 RAG？",
            "expected_keywords": [],
            "answerable": False,
            "negative_reason": "out_of_scope",
        },
        line_number=2,
    )
    assert negative.answerability is Answerability.NONE
    assert negative.negative_reason is NegativeReason.OUT_OF_SCOPE
    assert DIAGNOSTIC_ONLY_NOTE not in negative.tags

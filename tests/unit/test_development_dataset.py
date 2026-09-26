from __future__ import annotations

from collections import Counter
from pathlib import Path

from evals.schema import Answerability, LabelOrigin, NegativeReason, load_dataset

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / "evals" / "datasets" / "retrieval_development_v1.jsonl"


def _cases():  # type: ignore[no-untyped-def]
    return load_dataset(DATASET).cases


def test_development_dataset_has_planned_size_and_answerability_mix() -> None:
    cases = _cases()

    assert len(cases) == 60
    assert Counter(case.answerability for case in cases) == {
        Answerability.NONE: 35,
        Answerability.PARTIAL: 10,
        Answerability.FULL: 15,
    }
    assert all(case.split == "development" for case in cases)
    assert all(case.label_origin is LabelOrigin.HUMAN for case in cases)


def test_development_negatives_are_hard_and_explain_why_evidence_is_insufficient() -> None:
    negatives = [case for case in _cases() if case.answerability is Answerability.NONE]
    reasons = Counter(case.negative_reason for case in negatives)

    assert reasons == {
        NegativeReason.IN_DOMAIN_VALUE_MISSING: 7,
        NegativeReason.IN_DOMAIN_NO_CONCLUSION: 5,
        NegativeReason.VERSION_NOT_RELEASED: 5,
        NegativeReason.OUT_OF_RANGE_IMPLEMENTATION: 5,
        NegativeReason.FALSE_PREMISE: 8,
        NegativeReason.OUT_OF_SCOPE: 5,
    }
    assert all(case.negative_note for case in negatives)
    assert all(
        "hard_negative" in case.tags or "boundary_negative" in case.tags
        for case in negatives
    )


def test_development_partial_rows_identify_supported_and_missing_scope() -> None:
    partials = [case for case in _cases() if case.answerability is Answerability.PARTIAL]

    assert all(case.negative_reason is NegativeReason.PARTIAL_EVIDENCE_ONLY for case in partials)
    assert all(case.negative_note for case in partials)
    assert all(case.relevant_sources for case in partials)
    assert all(
        source.required_answer_points
        for case in partials
        for source in case.relevant_sources
    )


def test_development_full_rows_have_resolvable_answer_contracts() -> None:
    full_cases = [case for case in _cases() if case.answerability is Answerability.FULL]

    assert all(case.relevant_sources for case in full_cases)
    assert all(
        source.required_answer_points
        for case in full_cases
        for source in case.relevant_sources
    )

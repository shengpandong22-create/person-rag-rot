"""Guard that every regression label resolves against the real documents.

Why this test exists
--------------------
The runner resolves a label through ``document_logical_name`` +
``heading_path``.  When a path does not match exactly, the row degrades to
``keyword_fallback`` and silently drops out of formal Recall/MRR: the
evaluation still runs and still prints a number, it just measures fewer rows
than the dataset claims.

This happened once already — an abbreviated path such as
``["3.7 第二道防线：证据门禁"]`` was written where the parser produces
``["第 3 课：...", "一、教案正文", "3.7 第二道防线：证据门禁"]``, and all 25
references failed to resolve without any error being raised.  This test makes
that failure mode impossible to reintroduce unnoticed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.schema import Answerability, load_dataset

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / "evals" / "datasets" / "retrieval_regression_v1.jsonl"
DOCS_DIR = REPO_ROOT / "docs" / "learning"


def _document_paths() -> dict[str, set[tuple[str, ...]]]:
    from agent_mentor.rag.documents import DocumentParser

    parser = DocumentParser(max_pdf_pages=200)
    index: dict[str, set[tuple[str, ...]]] = {}
    for path in sorted(DOCS_DIR.glob("*.md")):
        index[path.stem] = {
            tuple(section.heading_path)
            for section in parser.parse(path.name, path.read_bytes())
            if section.heading_path
        }
    return index


@pytest.fixture(scope="module")
def document_paths() -> dict[str, set[tuple[str, ...]]]:
    assert DOCS_DIR.is_dir(), f"learning documents not found at {DOCS_DIR}"
    return _document_paths()


def test_regression_dataset_loads_in_strict_mode() -> None:
    """Every row must be fully graded; strict mode rejects unlabelled positives."""
    result = load_dataset(DATASET, require_graded=True)

    assert len(result.cases) == 30
    assert all(case.label_origin.value == "human" for case in result.cases)


def test_every_relevant_source_resolves_to_a_real_section(
    document_paths: dict[str, set[tuple[str, ...]]],
) -> None:
    result = load_dataset(DATASET, require_graded=False)
    unresolved: list[str] = []

    for case in result.cases:
        for source in case.relevant_sources:
            known = document_paths.get(source.document_logical_name)
            if known is None:
                unresolved.append(
                    f"{case.case_id}: unknown document {source.document_logical_name!r}"
                )
                continue
            if source.heading_path not in known:
                unresolved.append(
                    f"{case.case_id}: {' > '.join(source.heading_path)} "
                    f"(document {source.document_logical_name!r})"
                )

    assert not unresolved, (
        "these labels do not resolve and would silently drop out of Recall/MRR:\n"
        + "\n".join(f"  - {item}" for item in unresolved)
    )


def test_no_reference_uses_a_bare_section_suffix(
    document_paths: dict[str, set[tuple[str, ...]]],
) -> None:
    """A label must start with its document name, not jump straight to a section.

    Catching the abbreviated form explicitly gives a clearer failure message
    than the generic resolution check above.
    """
    result = load_dataset(DATASET, require_graded=False)
    offenders: list[str] = []

    for case in result.cases:
        for source in case.relevant_sources:
            if source.heading_path and source.heading_path[0] != source.document_logical_name:
                offenders.append(
                    f"{case.case_id}: path starts with "
                    f"{source.heading_path[0]!r}, expected "
                    f"{source.document_logical_name!r}"
                )

    assert not offenders, "abbreviated heading_path found:\n" + "\n".join(
        f"  - {item}" for item in offenders
    )


def test_answerable_rows_carry_answer_points(
    document_paths: dict[str, set[tuple[str, ...]]],
) -> None:
    """A graded label without answer points cannot be used as a rubric."""
    del document_paths
    result = load_dataset(DATASET, require_graded=False)
    missing: list[str] = []

    for case in result.cases:
        if case.answerability is Answerability.NONE:
            continue
        for source in case.relevant_sources:
            if not source.required_answer_points:
                missing.append(f"{case.case_id}: source without required_answer_points")

    assert not missing, "\n".join(f"  - {item}" for item in missing)


def test_negatives_declare_a_reason_for_stratification() -> None:
    """Easy and hard negatives must be distinguishable in the report."""
    result = load_dataset(DATASET, require_graded=False)
    negatives = [case for case in result.cases if case.answerability is Answerability.NONE]

    assert len(negatives) == 10
    assert all(case.negative_reason is not None for case in negatives)
    hard = [
        case
        for case in negatives
        if case.negative_reason is not None and case.negative_reason.value.startswith("in_domain")
    ]
    assert hard, "expected in-domain hard negatives after the human review"


def test_dataset_counts_match_the_reviewed_distribution() -> None:
    result = load_dataset(DATASET, require_graded=False)
    counts: dict[str, int] = {}
    for case in result.cases:
        counts[case.answerability.value] = counts.get(case.answerability.value, 0) + 1

    assert counts == {"full": 17, "partial": 3, "none": 10}


def test_partial_rows_explain_what_the_evidence_does_not_cover() -> None:
    result = load_dataset(DATASET, require_graded=False)
    partial = [case for case in result.cases if case.answerability is Answerability.PARTIAL]

    assert len(partial) == 3
    for case in partial:
        assert case.negative_reason is not None
        assert case.negative_note, f"{case.case_id} needs a note describing the gap"
        assert case.relevant_sources, f"{case.case_id} must cite what IS covered"

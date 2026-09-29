"""Guard that the dataset splits stay isolated and resolvable.

Why this matters for the ablation plan
--------------------------------------
Tuning is meant to happen on the validation split and be confirmed once on the
holdout split.  That only works if the splits are disjoint.  Two leaks are
possible and both are silent:

* the same question appearing in two splits, so tuning republishes its own
  answer as an acceptance result
* two differently-worded questions citing the exact same section set, which
  means the acceptance case is really just the tuning case wearing a hat

Neither shows up as a test failure on its own, so they are asserted here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.schema import Answerability, load_dataset

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASETS = REPO_ROOT / "evals" / "datasets"
DOCS_DIR = REPO_ROOT / "docs" / "learning"

SPLIT_FILES = {
    "development": (DATASETS / "retrieval_development_v1.jsonl", "development"),
    "regression": (DATASETS / "retrieval_regression_v1.jsonl", "regression"),
    "validation": (DATASETS / "retrieval_validation_v1.jsonl", "validation"),
    "holdout": (DATASETS / "retrieval_holdout_v1.jsonl", "holdout"),
    "quota4_acceptance": (
        DATASETS / "retrieval_quota4_acceptance_v1.jsonl",
        "acceptance",
    ),
    "same_heading_acceptance": (
        DATASETS / "retrieval_same_heading_acceptance_v1.jsonl",
        "acceptance",
    ),
}


def _load(name: str):  # type: ignore[no-untyped-def]
    return load_dataset(SPLIT_FILES[name][0], require_graded=False).cases


@pytest.fixture(scope="module")
def document_paths() -> dict[str, set[tuple[str, ...]]]:
    from agent_mentor.rag.documents import DocumentParser

    parser = DocumentParser(max_pdf_pages=200)
    return {
        path.stem: {
            tuple(section.heading_path)
            for section in parser.parse(path.name, path.read_bytes())
            if section.heading_path
        }
        for path in sorted(DOCS_DIR.glob("*.md"))
    }


def _normalise(text: str) -> str:
    return "".join(text.split()).casefold()


def _signature(case) -> frozenset[str]:  # type: ignore[no-untyped-def]
    return frozenset(
        f"{source.document_logical_name} > {' > '.join(source.heading_path)}"
        for source in case.relevant_sources
    )


@pytest.mark.parametrize("name", sorted(SPLIT_FILES))
def test_each_file_declares_expected_split(name: str) -> None:
    cases = _load(name)

    assert {case.split for case in cases} == {SPLIT_FILES[name][1]}


@pytest.mark.parametrize("name", sorted(SPLIT_FILES))
def test_every_split_is_fully_human_labelled(name: str) -> None:
    cases = _load(name)

    assert all(case.label_origin.value == "human" for case in cases)


def test_no_question_appears_in_two_splits() -> None:
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for name in SPLIT_FILES:
        for case in _load(name):
            key = _normalise(case.question)
            if key in seen:
                duplicates.append(f"{case.case_id} ({name}) duplicates {seen[key]}")
            seen[key] = f"{case.case_id} ({name})"

    assert not duplicates, "\n".join(duplicates)


def test_no_ground_truth_signature_is_shared_across_splits() -> None:
    """Sharing a section *within* a split is fine; sharing across splits is not.

    Several regression rows deliberately ask about the same section from
    different angles, which is useful coverage.  The leak that matters is a
    tuning row and an acceptance row resting on identical evidence, because
    then the acceptance result just re-measures the tuning case.
    """
    by_split = {
        name: {_signature(case) for case in _load(name) if _signature(case)}
        for name in SPLIT_FILES
    }
    duplicates: list[str] = []
    names = sorted(SPLIT_FILES)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            shared = by_split[left] & by_split[right]
            for signature in sorted(shared):
                duplicates.append(
                    f"{left} and {right} share a ground-truth signature: "
                    f"{sorted(signature)[0]}"
                )

    assert not duplicates, "\n".join(duplicates)


@pytest.mark.parametrize("name", sorted(SPLIT_FILES))
def test_all_labels_resolve_against_real_sections(
    name: str, document_paths: dict[str, set[tuple[str, ...]]]
) -> None:
    unresolved: list[str] = []
    for case in _load(name):
        for source in case.relevant_sources:
            known = document_paths.get(source.document_logical_name)
            if known is None or source.heading_path not in known:
                unresolved.append(f"{case.case_id}: {' > '.join(source.heading_path)}")

    assert not unresolved, "\n".join(unresolved)


@pytest.mark.parametrize("name", sorted(SPLIT_FILES))
def test_negatives_are_stratified_by_reason(name: str) -> None:
    """An aggregate rejection rate over only easy negatives proves nothing."""
    negatives = [case for case in _load(name) if case.answerability is Answerability.NONE]

    assert negatives, f"{name} has no negative rows"
    assert all(case.negative_reason is not None for case in negatives)


def test_holdout_contains_hard_negatives_not_only_out_of_scope() -> None:
    negatives = [
        case for case in _load("holdout") if case.answerability is Answerability.NONE
    ]
    reasons = {case.negative_reason.value for case in negatives if case.negative_reason}

    assert "out_of_scope" not in reasons or len(reasons) > 1
    assert any(reason.startswith("in_domain") for reason in reasons) or "false_premise" in reasons


def test_holdout_covers_topics_absent_from_validation() -> None:
    """The acceptance set must not be a rerun of the tuning set's topics."""
    validation_signatures = {_signature(case) for case in _load("validation")}
    holdout_signatures = {_signature(case) for case in _load("holdout") if _signature(case)}

    assert holdout_signatures - validation_signatures == holdout_signatures


def test_quota4_acceptance_is_independent_of_every_existing_split() -> None:
    acceptance = {
        _signature(case) for case in _load("quota4_acceptance") if _signature(case)
    }
    existing = {
        _signature(case)
        for name in ("development", "regression", "validation", "holdout")
        for case in _load(name)
        if _signature(case)
    }

    assert acceptance.isdisjoint(existing)


def test_same_heading_acceptance_is_independent_of_all_prior_datasets() -> None:
    acceptance = {
        _signature(case)
        for case in _load("same_heading_acceptance")
        if _signature(case)
    }
    prior = {
        _signature(case)
        for name in (
            "development",
            "regression",
            "validation",
            "holdout",
            "quota4_acceptance",
        )
        for case in _load(name)
        if _signature(case)
    }

    assert acceptance.isdisjoint(prior)

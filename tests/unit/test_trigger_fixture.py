from pathlib import Path

from evals.trigger_fixture import (
    check_trigger_freeze,
    load_and_validate_trigger_fixture,
)

DATASET = Path("evals/datasets/retrieval_trigger_development_v1.jsonl")
FREEZE = Path("evals/datasets/TRIGGER_DEVELOPMENT_FREEZE.json")


def test_trigger_development_fixture_is_balanced_and_independent() -> None:
    overlap_paths = tuple(
        path for path in Path("evals/datasets").glob("retrieval_*.jsonl") if path != DATASET
    )

    summary = load_and_validate_trigger_fixture(DATASET, overlap_paths=overlap_paths)

    assert summary.case_count == 16
    assert set(summary.scenario_counts.values()) == {4}
    assert summary.expected_trigger_counts == {"false": 8, "true": 8}


def test_trigger_development_freeze_is_intact() -> None:
    ok, message = check_trigger_freeze(DATASET, FREEZE)

    assert ok, message

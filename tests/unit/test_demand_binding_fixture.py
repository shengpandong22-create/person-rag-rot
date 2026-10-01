from pathlib import Path

from evals.demand_binding_fixture import check_freeze, load_and_validate

DATASET = Path("evals/datasets/retrieval_demand_binding_development_v1.jsonl")
MANIFEST = Path("evals/datasets/DEMAND_BINDING_DEVELOPMENT_FREEZE.json")


def test_demand_binding_fixture_is_balanced_independent_and_graded() -> None:
    others = tuple(Path("evals/datasets").glob("retrieval_*.jsonl"))
    summary = load_and_validate(DATASET, overlap_paths=others)

    assert summary["case_count"] == 15
    assert summary["feature_counts"] == {
        "cross_sentence": 3,
        "exact_value": 3,
        "range_value": 3,
        "table_value": 3,
        "unit_alias": 3,
    }
    assert summary["polarity_counts"] == {"negative": 5, "positive": 10}


def test_demand_binding_fixture_freeze_is_intact() -> None:
    ok, message = check_freeze(DATASET, MANIFEST)

    assert ok, message

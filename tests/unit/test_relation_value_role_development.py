from pathlib import Path

from evals.relation_value_role_development import _load, evaluate_rows

DATASET = Path("evals/datasets/relation_value_role_development_v1.jsonl")


def test_semantic_role_development_pairs_remain_balanced_and_pass() -> None:
    rows = _load(DATASET)
    result = evaluate_rows(rows)

    assert len(rows) == 12
    assert len({row["pair_id"] for row in rows}) == 6
    assert result["metrics"] == {
        "accuracy": 1.0,
        "positive_value_recall": 1.0,
        "negative_rejection": 1.0,
        "average_binding_count": 1.0,
        "max_binding_count": 3,
    }

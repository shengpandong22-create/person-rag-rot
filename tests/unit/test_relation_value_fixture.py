from pathlib import Path

from evals.relation_value_fixture import check_freeze, load_and_validate

DATASET = Path("evals/datasets/retrieval_relation_value_development_v1.jsonl")
MANIFEST = Path("evals/datasets/RELATION_VALUE_DEVELOPMENT_FREEZE.json")
BLIND_DATASET = Path("evals/datasets/retrieval_relation_value_blind_v1.jsonl")
BLIND_MANIFEST = Path("evals/datasets/RELATION_VALUE_BLIND_FREEZE.json")


def test_relation_value_fixture_is_balanced_independent_and_graded() -> None:
    summary = load_and_validate(
        DATASET, overlap_paths=tuple(Path("evals/datasets").glob("retrieval_*.jsonl"))
    )

    assert summary["case_count"] == 12
    assert summary["span_type_counts"] == {
        "bounded_multi_span": 3,
        "code_statement": 3,
        "sentence_span": 3,
        "table_row": 3,
    }
    assert summary["polarity_counts"] == {"negative": 4, "positive": 8}


def test_relation_value_fixture_freeze_is_intact() -> None:
    ok, message = check_freeze(DATASET, MANIFEST)

    assert ok, message


def test_relation_value_blind_fixture_meets_predeclared_composition() -> None:
    summary = load_and_validate(
        BLIND_DATASET,
        overlap_paths=(DATASET,),
        reject_source_overlap=True,
    )

    assert summary["case_count"] == 16
    assert summary["span_type_counts"] == {
        "bounded_multi_span": 4,
        "code_statement": 4,
        "sentence_span": 4,
        "table_row": 4,
    }
    assert summary["polarity_counts"] == {"negative": 6, "positive": 10}


def test_relation_value_blind_fixture_freeze_is_intact() -> None:
    ok, message = check_freeze(BLIND_DATASET, BLIND_MANIFEST)

    assert ok, message

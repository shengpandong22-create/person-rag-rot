import json
from pathlib import Path

import pytest

from evals.duplicate_pair_eval import binary_metrics, load_duplicate_pair_fixtures
from evals.freeze import file_sha256

DATASET = Path("evals/datasets/draft_claim_duplicate_pairs_development_v1.jsonl")
MANIFEST = Path("evals/datasets/DRAFT_CLAIM_DUPLICATE_PAIRS_DEVELOPMENT_FREEZE.json")


def test_duplicate_pair_fixture_is_balanced_and_covers_required_categories() -> None:
    fixtures = load_duplicate_pair_fixtures(DATASET)

    assert len(fixtures) == 22
    assert sum(fixture.expected_duplicate for fixture in fixtures) == 11
    assert {
        "pronoun",
        "alias",
        "nested_subject",
        "number",
        "date",
        "negation",
        "near_paraphrase",
    } == {fixture.category for fixture in fixtures}


def test_duplicate_pair_freeze_manifest_matches_dataset() -> None:
    record = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fixtures = load_duplicate_pair_fixtures(DATASET)

    assert record["sha256"] == file_sha256(DATASET)
    assert record["case_ids"] == [fixture.id for fixture in fixtures]


def test_binary_metrics_reports_precision_recall_and_confusion() -> None:
    metrics = binary_metrics([True, True, False, False], [True, False, True, False])

    assert metrics == {
        "precision": 0.5,
        "recall": 0.5,
        "f1": 0.5,
        "accuracy": 0.5,
        "true_positive": 1,
        "false_positive": 1,
        "false_negative": 1,
        "true_negative": 1,
    }


def test_duplicate_pair_loader_rejects_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "invalid.jsonl"
    path.write_text(
        '{"id":"x","category":"number","left":"a","right":"b",'
        '"expected_duplicate":true,"note":"n","extra":1}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_duplicate_pair_fixtures(path)

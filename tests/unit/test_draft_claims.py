from pathlib import Path

import pytest

from evals.draft_claim_eval import evaluate_fixture_predictions
from evals.draft_claims import DraftClaimOrigin, load_draft_claim_fixtures

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / "evals" / "datasets" / "draft_claim_nli_development_v1.jsonl"


def test_draft_claim_fixture_contract_is_balanced_and_human_owned() -> None:
    fixtures = load_draft_claim_fixtures(DATASET)

    assert len(fixtures) == 15
    assert all(item.claim.origin is DraftClaimOrigin.HUMAN_FIXTURE for item in fixtures)
    assert all(item.claim.required for item in fixtures)
    distribution = {
        status.value: sum(item.expected_status is status for item in fixtures)
        for status in set(item.expected_status for item in fixtures)
    }
    assert distribution == {
        "supported": 5,
        "contradicted": 5,
        "unknown": 5,
    }


def test_draft_claim_fixture_loader_rejects_duplicate_ids(tmp_path: Path) -> None:
    row = (
        '{"id":"same","evidence":"e","claim":{"id":"c","text":"t",'
        '"required":true,"origin":"human_fixture"},"expected_status":"unknown","note":"n"}'
    )
    path = tmp_path / "duplicate.jsonl"
    path.write_text(f"{row}\n{row}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate fixture id"):
        load_draft_claim_fixtures(path)


def test_fixture_metrics_report_three_way_confusion() -> None:
    metrics = evaluate_fixture_predictions(
        ["supported", "contradicted", "unknown"],
        ["supported", "unknown", "unknown"],
    )

    assert metrics["accuracy"] == 0.6667
    assert metrics["macro_accuracy"] == 0.6667
    assert metrics["confusion_matrix"] == {
        "supported": {"supported": 1, "contradicted": 0, "unknown": 0},
        "contradicted": {"supported": 0, "contradicted": 0, "unknown": 1},
        "unknown": {"supported": 0, "contradicted": 0, "unknown": 1},
    }

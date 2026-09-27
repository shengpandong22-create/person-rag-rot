import json
from pathlib import Path

import pytest

from evals.claim_extractor_stability import compute_stability_metrics, verify_freeze

DATASET = Path("evals/datasets/draft_claim_extraction_development_v2.jsonl")
MANIFEST = Path("evals/datasets/DRAFT_CLAIM_EXTRACTION_DEVELOPMENT_FREEZE.json")


def _run(claims: list[str], recall: float = 1.0) -> dict[str, object]:
    return {
        "metrics": {
            "schema_valid_rate": 1.0,
            "required_claim_recall": recall,
            "extra_claim_rate": 0.0,
            "unsupported_claim_rate": 0.0,
            "nli_retained_claim_rate": 1.0,
            "semantic_duplicate_rate": 0.0,
        },
        "cases": [
            {
                "id": "case-1",
                "extracted_claims": [{"text": text} for text in claims],
            }
        ],
    }


def test_compute_stability_metrics_reports_exact_and_pairwise_consistency() -> None:
    metrics = compute_stability_metrics(
        [_run(["声明一", "声明二"]), _run(["声明一", "声明二"]), _run(["声明一"], 0.5)]
    )

    assert metrics["exact_claim_set_stability_rate"] == 0.0
    assert metrics["mean_pairwise_claim_jaccard"] == 0.6667
    assert metrics["required_claim_recall_min"] == 0.5
    assert metrics["required_claim_recall_max"] == 1.0


def test_verify_freeze_accepts_manifest_and_rejects_changed_dataset(tmp_path: Path) -> None:
    record = verify_freeze(DATASET, MANIFEST)
    assert record["case_count"] == 15

    changed = tmp_path / "changed.jsonl"
    changed.write_text(DATASET.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_freeze(changed, MANIFEST)


def test_freeze_manifest_case_ids_match_dataset() -> None:
    record = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = [json.loads(line)["id"] for line in DATASET.read_text(encoding="utf-8").splitlines()]

    assert record["case_ids"] == ids

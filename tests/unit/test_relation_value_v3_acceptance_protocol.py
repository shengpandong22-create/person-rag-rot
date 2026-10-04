import hashlib
import json
from pathlib import Path
from typing import Any

from evals.relation_value_v3_acceptance_audit import load_jsonl
from evals.relation_value_v3_acceptance_freeze import verify_manifest
from evals.relation_value_v3_freeze import verify_manifest as verify_candidate_manifest

THRESHOLDS = Path("evals/datasets/RELATION_VALUE_V3_ACCEPTANCE_THRESHOLDS.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _thresholds() -> dict[str, Any]:
    return json.loads(THRESHOLDS.read_text(encoding="utf-8"))


def test_acceptance_protocol_frozen_inputs_are_intact() -> None:
    thresholds = _thresholds()
    candidate_manifest = Path(thresholds["candidate_freeze_manifest"])
    acceptance_manifest = Path(thresholds["acceptance_freeze_manifest"])

    candidate_intact, candidate_result = verify_candidate_manifest(candidate_manifest)
    acceptance_intact, acceptance_result = verify_manifest(acceptance_manifest)

    assert candidate_intact, candidate_result
    assert acceptance_intact, acceptance_result
    assert _sha256(candidate_manifest) == thresholds["candidate_freeze_manifest_sha256"]
    assert _sha256(acceptance_manifest) == thresholds["acceptance_freeze_manifest_sha256"]


def test_acceptance_protocol_counts_match_frozen_dataset() -> None:
    thresholds = _thresholds()
    dataset = Path(thresholds["acceptance_dataset"])
    rows = load_jsonl(dataset)
    positives = [row for row in rows if row["answerability"] == "full"]
    negatives = [row for row in rows if row["answerability"] == "none"]
    counts = thresholds["expected_counts"]

    assert _sha256(dataset) == thresholds["acceptance_dataset_sha256"]
    assert len(rows) == counts["rows"]
    assert len(positives) == counts["positive_rows"]
    assert len(negatives) == counts["negative_rows"]
    assert sum(len(row["demands"]) for row in rows) == counts["demands"]
    assert sum(len(row["demands"]) for row in positives) == counts["positive_demands"]
    assert sum(len(row["demands"]) for row in negatives) == counts["negative_demands"]
    assert sum(len(row["demands"]) > 1 for row in rows) == counts["multi_demand_rows"]
    assert len({row["pair_id"] for row in rows if row.get("pair_id")}) == counts[
        "paired_groups"
    ]


def test_acceptance_protocol_keeps_execution_one_shot_and_eval_only() -> None:
    thresholds = _thresholds()
    contract = thresholds["evaluation_contract"]
    execution = thresholds["execution"]

    assert contract["input_mode"] == "labeled_evidence_spans_only"
    assert contract["retrieval_allowed"] is False
    assert contract["database_lookup_allowed"] is False
    assert contract["model_inference_allowed"] is False
    assert execution["completed_runs_allowed"] == 1
    assert execution["acceptance_driven_candidate_tuning_allowed"] is False
    assert execution["production_integration_authorized"] is False


def test_acceptance_protocol_negative_gates_are_strict() -> None:
    gates = _thresholds()["hard_gates"]

    assert gates["negative_demand_rejection_required"] == 1.0
    assert gates["negative_row_rejection_required"] == 1.0
    assert set(gates["negative_category_rejection_required"].values()) == {1.0}
    assert gates["candidate_freeze_intact_before_and_after_required"] is True
    assert gates["acceptance_freeze_intact_before_and_after_required"] is True
    assert gates["production_imports_candidate_required"] is False

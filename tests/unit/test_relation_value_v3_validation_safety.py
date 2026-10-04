import copy
import json
from pathlib import Path

from evals.relation_value_v3_validation_safety import evaluate_safety

THRESHOLDS = Path("evals/datasets/RELATION_VALUE_V3_VALIDATION_THRESHOLDS.json")
REFERENCE = Path(
    "evals/reports/validation_heading_candidate_ablation/vector_only/retrieval_eval.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _compatible_reference() -> dict:
    report = _load(REFERENCE)
    report["metadata"]["supplemental_consumption"] = "none"
    report["metadata"]["demand_binding_policy"] = "none"
    return report


def test_reference_metrics_pass_predeclared_validation_safety_gates() -> None:
    thresholds = _load(THRESHOLDS)
    result = evaluate_safety(
        thresholds,
        _compatible_reference(),
        validation_freeze_hash=thresholds["validation_freeze_manifest_sha256"],
        candidate_freeze_intact=True,
        production_imports_candidate=False,
    )

    assert result["safe_for_next_protocol"]
    assert all(result["checks"].values())


def test_partial_accuracy_regression_blocks_progression() -> None:
    thresholds = _load(THRESHOLDS)
    report = copy.deepcopy(_compatible_reference())
    report["metrics"]["partial_answerability_accuracy"] = 0.5

    result = evaluate_safety(
        thresholds,
        report,
        validation_freeze_hash=thresholds["validation_freeze_manifest_sha256"],
        candidate_freeze_intact=True,
        production_imports_candidate=False,
    )

    assert not result["safe_for_next_protocol"]
    assert not result["checks"]["partial_answerability_accuracy"]


def test_changed_validation_freeze_blocks_progression() -> None:
    result = evaluate_safety(
        _load(THRESHOLDS),
        _compatible_reference(),
        validation_freeze_hash="changed",
        candidate_freeze_intact=True,
        production_imports_candidate=False,
    )

    assert not result["safe_for_next_protocol"]
    assert not result["checks"]["validation_freeze_hash"]

import copy
import json
from pathlib import Path

from evals.relation_value_v3_regression_safety import (
    evaluate_safety,
    production_imports_candidate,
)

THRESHOLDS = Path("evals/datasets/RELATION_VALUE_V3_REGRESSION_THRESHOLDS.json")
REPORT = Path("evals/reports/relation_value_v3_regression_safety/retrieval_eval.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_completed_regression_run_passes_predeclared_safety_gates() -> None:
    result = evaluate_safety(
        _load(THRESHOLDS),
        _load(REPORT),
        freeze_intact=True,
        production_imports_candidate=False,
    )

    assert result["safe_for_next_protocol"]
    assert all(result["checks"].values())


def test_metric_regression_blocks_progression() -> None:
    report = copy.deepcopy(_load(REPORT))
    report["metrics"]["recall_at_6"] = 0.44

    result = evaluate_safety(
        _load(THRESHOLDS),
        report,
        freeze_intact=True,
        production_imports_candidate=False,
    )

    assert not result["safe_for_next_protocol"]
    assert not result["checks"]["recall_at_6"]


def test_production_source_does_not_import_eval_only_candidate() -> None:
    assert not production_imports_candidate()

import copy
import json
from pathlib import Path

from evals.relation_value_v3_qualification import qualify

THRESHOLDS = Path("evals/datasets/RELATION_VALUE_V3_FREEZE_THRESHOLDS.json")
ORIGINAL = Path("evals/reports/relation_value_binding_v3_development/result.json")
ROLE = Path("evals/reports/relation_value_role_development_v1/result.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_v3_reports_meet_predeclared_freeze_gates() -> None:
    result = qualify(_load(THRESHOLDS), _load(ORIGINAL), _load(ROLE))

    assert result["qualified_for_freeze"]
    assert all(result["checks"].values())


def test_any_hard_gate_failure_blocks_freeze() -> None:
    role = copy.deepcopy(_load(ROLE))
    role["metrics"]["negative_rejection"] = 0.99

    result = qualify(_load(THRESHOLDS), _load(ORIGINAL), role)

    assert not result["qualified_for_freeze"]
    assert not result["checks"]["role_negative_rejection"]

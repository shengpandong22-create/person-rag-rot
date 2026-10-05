from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

THRESHOLDS = {
    "schema_valid_rate": 0.95,
    "tool_selection_accuracy": 0.90,
    "recommendation_action_accuracy": 0.85,
    "max_step_adherence": 1.0,
    "confirmation_guard_rate": 1.0,
    "business_zero_write_rate": 1.0,
    "decision_stability": 0.85,
    "latency_p95_ms": 15000.0,
}


def judge(report: dict[str, Any]) -> dict[str, object]:
    metrics = cast(dict[str, float], report["metrics"])
    checks: dict[str, bool] = {}
    for name, threshold in THRESHOLDS.items():
        value = metrics[name]
        checks[name] = value <= threshold if name == "latency_p95_ms" else value >= threshold
    return {
        "eligible": all(checks.values()),
        "checks": checks,
        "metrics": {name: metrics[name] for name in THRESHOLDS},
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Judge a frozen Shadow Agent semantic report.")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    result = judge(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

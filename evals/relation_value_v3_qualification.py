"""Evaluate V3 Development reports against predeclared freeze gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def qualify(
    thresholds: dict[str, Any],
    original_report: dict[str, Any],
    role_report: dict[str, Any],
) -> dict[str, Any]:
    original_limits = thresholds["original_development"]
    role_limits = thresholds["semantic_role_development"]
    original = original_report["metrics"]
    role = role_report["metrics"]
    pairs: dict[str, list[dict[str, Any]]] = {}
    for case in role_report["cases"]:
        pairs.setdefault(str(case["pair_id"]), []).append(case)
    pair_integrity = (
        len(pairs) == role_limits["pair_count_required"]
        and all(
            len(cases) == 2 and all(case["correct"] for case in cases)
            for cases in pairs.values()
        )
    )
    checks = {
        "original_accuracy": original["provenance_aware_binding_accuracy"]
        >= original_limits["provenance_aware_binding_accuracy_min"],
        "original_labeled_recall": original["labeled_binding_recall"]
        >= original_limits["labeled_binding_recall_min"],
        "original_negative_rejection": original["negative_rejection"]
        == original_limits["negative_rejection_required"],
        "original_each_span_type": all(
            count >= original_limits["each_span_type_success_min"]
            for count in original["span_success_counts"].values()
        ),
        "original_average_binding_count": original["average_binding_count"]
        <= original_limits["average_binding_count_max"],
        "original_max_binding_count": original["max_binding_count"]
        <= original_limits["max_binding_count_max"],
        "original_max_bindings_per_chunk": original["max_bindings_per_chunk"]
        <= original_limits["max_bindings_per_chunk_max"],
        "role_accuracy": role["accuracy"] == role_limits["accuracy_required"],
        "role_positive_value_recall": role["positive_value_recall"]
        == role_limits["positive_value_recall_required"],
        "role_negative_rejection": role["negative_rejection"]
        == role_limits["negative_rejection_required"],
        "role_pair_integrity": pair_integrity,
        "role_average_binding_count": role["average_binding_count"]
        <= role_limits["average_binding_count_max"],
        "role_max_binding_count": role["max_binding_count"]
        <= role_limits["max_binding_count_max"],
    }
    return {
        "candidate": thresholds["candidate"],
        "candidate_commit": thresholds["candidate_commit"],
        "qualified_for_freeze": all(checks.values()),
        "checks": checks,
        "observed": {
            "original_development": original,
            "semantic_role_development": role,
            "semantic_role_pair_count": len(pairs),
        },
    }


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thresholds", required=True, type=Path)
    parser.add_argument("--original-report", required=True, type=Path)
    parser.add_argument("--role-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = qualify(_load(args.thresholds), _load(args.original_report), _load(args.role_report))
    result["evaluated_git_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    result["artifacts"] = {
        "thresholds": {"path": str(args.thresholds), "sha256": _sha256(args.thresholds)},
        "original_report": {
            "path": str(args.original_report),
            "sha256": _sha256(args.original_report),
        },
        "role_report": {"path": str(args.role_report), "sha256": _sha256(args.role_report)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

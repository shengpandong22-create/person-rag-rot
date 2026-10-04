"""Score the frozen V3 candidate's cross-split validation safety run."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from evals.relation_value_v3_freeze import verify_manifest
from evals.relation_value_v3_regression_safety import production_imports_candidate

CANDIDATE_FREEZE_MANIFEST = Path(
    "evals/datasets/RELATION_VALUE_V3_CANDIDATE_FREEZE.json"
)


def evaluate_safety(
    thresholds: dict[str, Any],
    report: dict[str, Any],
    *,
    validation_freeze_hash: str,
    candidate_freeze_intact: bool,
    production_imports_candidate: bool,
) -> dict[str, Any]:
    gates = thresholds["gates"]
    expected = thresholds["configuration"]
    metrics = report["metrics"]
    metadata = report["metadata"]
    config_checks = {
        "experiment_mode": metadata["experiment_mode"] == expected["experiment_mode"],
        "top_k": metadata["retrieval_top_k"] == expected["top_k"],
        "candidate_k": metadata["retrieval_candidate_k"] == expected["candidate_k"],
        "max_chunks_per_document": metadata["retrieval_max_chunks_per_document"]
        == expected["max_chunks_per_document"],
        "query_strategy": metadata["query_strategy"] == expected["query_strategy"],
        "candidate_expansion": metadata["candidate_expansion"]
        == expected["candidate_expansion"],
        "supplemental_consumption": metadata["supplemental_consumption"]
        == expected["supplemental_consumption"],
        "demand_binding_policy": metadata["demand_binding_policy"]
        == expected["demand_binding_policy"],
        "evidence_gate_policy": metadata["evidence_gate_policy"]
        == expected["evidence_gate_policy"],
    }
    checks = {
        "dataset_hash": metadata["dataset_sha256"] == thresholds["dataset_sha256"],
        "validation_freeze_hash": validation_freeze_hash
        == thresholds["validation_freeze_manifest_sha256"],
        "configuration": all(config_checks.values()),
        "recall_at_1": metrics["recall_at_1"] >= gates["recall_at_1_min"],
        "recall_at_3": metrics["recall_at_3"] >= gates["recall_at_3_min"],
        "recall_at_6": metrics["recall_at_6"] >= gates["recall_at_6_min"],
        "mrr": metrics["mrr"] >= gates["mrr_min"],
        "full_answerability_accuracy": metrics["full_answerability_accuracy"]
        == gates["full_answerability_accuracy_required"],
        "partial_answerability_accuracy": metrics["partial_answerability_accuracy"]
        == gates["partial_answerability_accuracy_required"],
        "negative_rejection_accuracy": metrics["negative_rejection_accuracy"]
        == gates["negative_rejection_accuracy_required"],
        "candidate_recall_at_20": metrics["candidate_recall_at_20"]
        >= gates["candidate_recall_at_20_min"],
        "average_candidate_count": metrics["average_candidate_count"]
        == gates["average_candidate_count_required"],
        "latency_p95_ms": metrics["latency_p95_ms"] <= gates["latency_p95_ms_max"],
        "graded_rows": metadata["grading_counts"]["graded"]
        == gates["graded_rows_required"],
        "resolved_labels": metadata["ground_truth_counts"]["resolved"]
        == gates["resolved_labels_required"],
        "candidate_freeze_intact": candidate_freeze_intact,
        "production_isolation": not production_imports_candidate,
    }
    return {
        "candidate": thresholds["candidate"],
        "safe_for_next_protocol": all(checks.values()),
        "checks": checks,
        "configuration_checks": config_checks,
        "observed_metrics": {
            key: metrics[key]
            for key in (
                "recall_at_1",
                "recall_at_3",
                "recall_at_6",
                "mrr",
                "full_answerability_accuracy",
                "partial_answerability_accuracy",
                "negative_rejection_accuracy",
                "candidate_recall_at_20",
                "average_candidate_count",
                "latency_p50_ms",
                "latency_p95_ms",
            )
        },
    }


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thresholds", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    thresholds = _load(args.thresholds)
    validation_freeze = Path(thresholds["validation_freeze_manifest"])
    freeze_intact, freeze_result = verify_manifest(CANDIDATE_FREEZE_MANIFEST)
    result = evaluate_safety(
        thresholds,
        _load(args.report),
        validation_freeze_hash=_sha256(validation_freeze),
        candidate_freeze_intact=freeze_intact,
        production_imports_candidate=production_imports_candidate(),
    )
    result["evaluated_git_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    result["artifacts"] = {
        "thresholds": {"path": str(args.thresholds), "sha256": _sha256(args.thresholds)},
        "report": {"path": str(args.report), "sha256": _sha256(args.report)},
        "validation_freeze": {
            "path": str(validation_freeze),
            "sha256": _sha256(validation_freeze),
        },
        "candidate_freeze": freeze_result,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Score a completed relation-value blind run against predeclared gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def score_qualification(
    dataset_rows: list[dict[str, Any]],
    retrieval_cases: list[dict[str, Any]],
    binding_result: dict[str, Any],
) -> dict[str, Any]:
    labels = {str(row["id"]): row for row in dataset_rows}
    retrieval = {str(case["id"]): case for case in retrieval_cases}
    bindings = {str(case["id"]): case for case in binding_result["cases"]}
    positive_ids = [case_id for case_id, row in labels.items() if row["expected_binding"]]
    negative_ids = [case_id for case_id, row in labels.items() if not row["expected_binding"]]
    available_ids = [
        case_id
        for case_id in positive_ids
        if any(
            item.get("matched_ground_truth")
            for item in [
                *(retrieval[case_id].get("top_chunks") or []),
                *(retrieval[case_id].get("supplemental_chunks") or []),
            ]
        )
    ]
    correct_ids = [
        case_id for case_id in positive_ids if bindings[case_id]["correct_labeled_binding"]
    ]
    wrong_provenance_only = [
        case_id
        for case_id in positive_ids
        if bindings[case_id]["predicted_binding"]
        and not bindings[case_id]["correct_labeled_binding"]
    ]
    rejected_negative_ids = [
        case_id for case_id in negative_ids if not bindings[case_id]["predicted_binding"]
    ]
    span_success = {
        span_type: sum(
            case_id in correct_ids
            for case_id in positive_ids
            if labels[case_id]["evidence_span_type"] == span_type
        )
        for span_type in sorted({str(row["evidence_span_type"]) for row in labels.values()})
    }
    accuracy = (len(correct_ids) + len(rejected_negative_ids)) / len(labels)
    labeled_recall = len(correct_ids) / len(positive_ids)
    conditional_recall = len(set(correct_ids) & set(available_ids)) / len(available_ids)
    negative_rejection = len(rejected_negative_ids) / len(negative_ids)
    checks = {
        "provenance_aware_accuracy_gte_0_85": accuracy >= 0.85,
        "labeled_binding_recall_gte_0_80": labeled_recall >= 0.80,
        "conditional_binding_recall_gte_0_90": conditional_recall >= 0.90,
        "negative_rejection_eq_1": negative_rejection == 1.0,
        "wrong_provenance_only_acceptance_eq_0": not wrong_provenance_only,
        "each_span_type_has_success": all(count >= 1 for count in span_success.values()),
    }
    return {
        "qualified": all(checks.values()),
        "metrics": {
            "provenance_aware_binding_accuracy": round(accuracy, 4),
            "labeled_binding_recall": round(labeled_recall, 4),
            "conditional_labeled_binding_recall": round(conditional_recall, 4),
            "negative_rejection": round(negative_rejection, 4),
            "wrong_provenance_only_acceptance_count": len(wrong_provenance_only),
            "available_positive_count": len(available_ids),
            "positive_count": len(positive_ids),
            "span_success_counts": span_success,
        },
        "checks": checks,
        "failures": {
            "candidate_recall_miss": sorted(set(positive_ids) - set(available_ids)),
            "available_but_unbound": sorted(set(available_ids) - set(correct_ids)),
            "wrong_provenance_only_acceptance": sorted(wrong_provenance_only),
            "false_acceptance": sorted(set(negative_ids) - set(rejected_negative_ids)),
        },
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("//")
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--retrieval-report", required=True, type=Path)
    parser.add_argument("--binding-result", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    retrieval = json.loads(args.retrieval_report.read_text(encoding="utf-8"))
    binding = json.loads(args.binding_result.read_text(encoding="utf-8"))
    result = score_qualification(_load_jsonl(args.dataset), retrieval["cases"], binding)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

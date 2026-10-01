from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def analyze_low_overlap_recall(cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [case for case in cases if "low_overlap_semantic_positive" in case.get("tags", [])]
    categories: Counter[str] = Counter()
    details: list[dict[str, Any]] = []
    for case in rows:
        raw_rank = case.get("first_raw_candidate_rank")
        final_rank = case.get("first_relevant_rank")
        supplemental_rank = case.get("first_supplemental_rank")
        if raw_rank is None:
            loss = "vector_candidate_miss"
        elif final_rank is None:
            loss = "ranking_cutoff"
        else:
            loss = "primary_hit"
        categories[loss] += 1
        details.append(
            {
                "case_id": case["id"],
                "loss_stage": loss,
                "raw_rank": raw_rank,
                "post_filter_rank": case.get("first_post_filter_rank"),
                "final_rank": final_rank,
                "supplemental_rank": supplemental_rank,
                "heading_recovers_at_20": (
                    supplemental_rank is not None and int(supplemental_rank) <= 20
                ),
            }
        )
    return {
        "total": len(rows),
        "loss_stage_counts": dict(sorted(categories.items())),
        "vector_candidate_recall_at_20": _rate(
            sum(item["raw_rank"] is not None and int(item["raw_rank"]) <= 20 for item in details),
            len(details),
        ),
        "primary_recall_at_6": _rate(
            sum(
                item["final_rank"] is not None and int(item["final_rank"]) <= 6 for item in details
            ),
            len(details),
        ),
        "heading_supplemental_recall_at_20": _rate(
            sum(bool(item["heading_recovers_at_20"]) for item in details), len(details)
        ),
        "details": details,
    }


def analyze_heading_negative_gate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [case for case in cases if "heading_similar_negative" in case.get("tags", [])]
    causes: Counter[str] = Counter()
    details: list[dict[str, Any]] = []
    for case in rows:
        assessment = dict(case["evidence_assessment"])
        requested = list(assessment.get("numeric_tokens_requested") or [])
        covered = list(assessment.get("numeric_tokens_covered") or [])
        exact_assessments = [
            item
            for item in assessment.get("demand_assessments") or []
            if item.get("demand_type") == "exact_value"
        ]
        if requested and not covered and assessment.get("production_sufficient"):
            cause = "explicit_number_not_enforced"
        elif any(item.get("matched_signals") for item in exact_assessments):
            cause = "unbound_incidental_number"
        else:
            cause = "lexical_support_without_conclusion"
        causes[cause] += 1
        details.append(
            {
                "case_id": case["id"],
                "decision": assessment.get("decision"),
                "coverage_ratio": assessment.get("coverage_ratio"),
                "numeric_tokens_requested": requested,
                "numeric_tokens_covered": covered,
                "demand_markers": list(assessment.get("demand_markers") or []),
                "exact_value_matched_signals": [
                    signal
                    for item in exact_assessments
                    for signal in item.get("matched_signals") or []
                ],
                "root_cause": cause,
            }
        )
    return {
        "total": len(rows),
        "false_acceptance_count": sum(item["decision"] == "full" for item in details),
        "root_cause_counts": dict(sorted(causes.items())),
        "details": details,
    }


def _rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split trigger fixture retrieval/Gate diagnostics."
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    cases = list(report["cases"])
    result = {
        "source_report": str(args.report),
        "low_overlap_recall": analyze_low_overlap_recall(cases),
        "heading_negative_gate": analyze_heading_negative_gate(cases),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

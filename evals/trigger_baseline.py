from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from evals.retrieval_uncertainty import _classification_metrics, extract_uncertainty_row

PREDECLARED_RULES = {
    "overlap_high": lambda overlap, score: overlap >= 0.416667,
    "heading_score_high": lambda overlap, score: score >= 10.0,
    "overlap_and_score": lambda overlap, score: overlap >= 0.363636 and score >= 10.0,
    "overlap_or_very_high_score": lambda overlap, score: overlap >= 0.416667 or score >= 22.0,
}


def analyze_trigger_baseline(
    fixture_rows: list[dict[str, Any]], report_cases: list[dict[str, Any]]
) -> dict[str, Any]:
    reports = {str(case["id"]): case for case in report_cases}
    rows: list[dict[str, Any]] = []
    for fixture in fixture_rows:
        case_id = str(fixture["id"])
        report_case = reports[case_id]
        feature = extract_uncertainty_row(report_case)
        rows.append(
            {
                "case_id": case_id,
                "scenario": str(fixture["trigger_scenario"]),
                "expected_trigger": bool(fixture["expected_trigger"]),
                "actual_recoverable": feature.recoverable_miss,
                "primary_relevant_rank": report_case.get("first_relevant_rank"),
                "raw_relevant_rank": report_case.get("first_raw_candidate_rank"),
                "supplemental_relevant_rank": report_case.get("first_supplemental_rank"),
                "vector_top1_score": feature.vector_top1_score,
                "demand_heading_overlap": feature.demand_heading_overlap,
                "supplemental_heading_score": feature.supplemental_heading_score,
                "primary_gate_reject": feature.primary_gate_reject,
            }
        )

    expected = [bool(row["expected_trigger"]) for row in rows]
    recoverable = [bool(row["actual_recoverable"]) for row in rows]
    rule_results: dict[str, Any] = {}
    for name, rule in PREDECLARED_RULES.items():
        predictions = [
            rule(
                float(row["demand_heading_overlap"]),
                float(row["supplemental_heading_score"]),
            )
            for row in rows
        ]
        rule_results[name] = {
            "against_expected_trigger": _classification_metrics(predictions, expected),
            "against_actual_recoverable": _classification_metrics(predictions, recoverable),
            "triggered_case_ids": [
                str(row["case_id"])
                for prediction, row in zip(predictions, rows, strict=True)
                if prediction
            ],
        }

    scenario_summary: dict[str, Any] = {}
    for scenario in sorted({str(row["scenario"]) for row in rows}):
        selected = [row for row in rows if row["scenario"] == scenario]
        scenario_summary[scenario] = {
            "count": len(selected),
            "primary_top6_hits": sum(row["primary_relevant_rank"] is not None for row in selected),
            "supplemental_at_1_hits": sum(
                row["supplemental_relevant_rank"] == 1 for row in selected
            ),
            "supplemental_at_20_hits": sum(
                row["supplemental_relevant_rank"] is not None
                and int(row["supplemental_relevant_rank"]) <= 20
                for row in selected
            ),
            "gate_rejections": sum(bool(row["primary_gate_reject"]) for row in selected),
        }

    return {
        "case_count": len(rows),
        "expected_trigger_count": sum(expected),
        "actual_recoverable_count": sum(recoverable),
        "expected_vs_actual": {
            "both_true": sum(e and a for e, a in zip(expected, recoverable, strict=True)),
            "expected_only": sum(e and not a for e, a in zip(expected, recoverable, strict=True)),
            "actual_only": sum(not e and a for e, a in zip(expected, recoverable, strict=True)),
            "both_false": sum(not e and not a for e, a in zip(expected, recoverable, strict=True)),
        },
        "scenario_summary": scenario_summary,
        "rule_results": rule_results,
        "failure_categories": dict(
            sorted(Counter(str(case.get("failure_category")) for case in report_cases).items())
        ),
        "rows": rows,
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("//")
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Characterize frozen trigger fixture baseline.")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fixture_rows = _load_jsonl(args.fixture)
    report = json.loads(args.report.read_text(encoding="utf-8"))
    result = analyze_trigger_baseline(fixture_rows, list(report["cases"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "rows"},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

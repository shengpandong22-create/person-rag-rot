from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class GatePolicyResult:
    policy: str
    parameters: dict[str, object]
    full_acceptance_rate: float
    partial_boundary_detection_rate: float
    none_rejection_rate: float
    macro_accuracy: float
    confusion_matrix: dict[str, dict[str, int]]
    rejection_by_negative_reason: dict[str, float]
    false_full_case_ids: tuple[str, ...]
    false_rejection_case_ids: tuple[str, ...]


def replay_report(report: dict[str, Any]) -> list[GatePolicyResult]:
    rows = report["cases"]
    policies: list[tuple[str, dict[str, object]]] = [("current_binary_v1", {})]
    policies.extend(
        ("specific_coverage_ratio", {"minimum": threshold})
        for threshold in (0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5)
    )
    policies.extend(
        ("specific_covered_terms", {"minimum": minimum}) for minimum in range(2, 9)
    )
    policies.append(("numeric_demand_coverage", {}))
    return [_evaluate_policy(rows, name, parameters) for name, parameters in policies]


def eligible_candidates(results: list[GatePolicyResult]) -> list[GatePolicyResult]:
    baseline = results[0]
    return sorted(
        (
            result
            for result in results[1:]
            if result.full_acceptance_rate >= 0.9
            and result.none_rejection_rate > baseline.none_rejection_rate
            and all(
                rate >= baseline.rejection_by_negative_reason.get(reason, 0.0)
                for reason, rate in result.rejection_by_negative_reason.items()
            )
        ),
        key=lambda item: (
            item.macro_accuracy,
            item.none_rejection_rate,
            item.partial_boundary_detection_rate,
        ),
        reverse=True,
    )


def _evaluate_policy(
    rows: list[dict[str, Any]], name: str, parameters: dict[str, object]
) -> GatePolicyResult:
    predictions = {row["id"]: _predict(row, name, parameters) for row in rows}
    labels = ("full", "partial", "none")
    confusion = {
        actual: {
            predicted: sum(
                row["answerability"] == actual and predictions[row["id"]] == predicted
                for row in rows
            )
            for predicted in labels
        }
        for actual in labels
    }
    grouped_negatives: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["answerability"] == "none":
            grouped_negatives.setdefault(row["negative_reason"] or "unspecified", []).append(row)
    class_accuracy = {
        label: _rate(
            predictions[row["id"]] == label for row in rows if row["answerability"] == label
        )
        for label in labels
    }
    false_full = tuple(
        row["id"]
        for row in rows
        if row["answerability"] != "full" and predictions[row["id"]] == "full"
    )
    false_rejections = tuple(
        row["id"]
        for row in rows
        if row["answerability"] == "full" and predictions[row["id"]] != "full"
    )
    return GatePolicyResult(
        policy=name,
        parameters=parameters,
        full_acceptance_rate=class_accuracy["full"],
        partial_boundary_detection_rate=class_accuracy["partial"],
        none_rejection_rate=_rate(
            predictions[row["id"]] != "full"
            for row in rows
            if row["answerability"] == "none"
        ),
        macro_accuracy=round(sum(class_accuracy.values()) / len(class_accuracy), 4),
        confusion_matrix=confusion,
        rejection_by_negative_reason={
            reason: _rate(predictions[row["id"]] != "full" for row in group)
            for reason, group in sorted(grouped_negatives.items())
        },
        false_full_case_ids=false_full,
        false_rejection_case_ids=false_rejections,
    )


def _predict(row: dict[str, Any], name: str, parameters: dict[str, object]) -> str:
    assessment = row["evidence_assessment"]
    if not assessment["production_sufficient"]:
        return "none"
    if name == "current_binary_v1":
        return "full"
    if name == "specific_coverage_ratio":
        minimum = parameters["minimum"]
        if not isinstance(minimum, (int, float)):
            raise TypeError("specific coverage minimum must be numeric")
        return (
            "full"
            if float(assessment["coverage_ratio"]) >= float(minimum)
            else "partial"
        )
    if name == "specific_covered_terms":
        minimum = parameters["minimum"]
        if not isinstance(minimum, int):
            raise TypeError("specific covered terms minimum must be an integer")
        specific = set(assessment["specific_query_terms"])
        covered = set(assessment["covered_terms"])
        return "full" if len(specific & covered) >= minimum else "partial"
    if name == "numeric_demand_coverage":
        requested = set(assessment["numeric_tokens_requested"])
        covered = set(assessment["numeric_tokens_covered"])
        return "partial" if requested - covered else "full"
    raise ValueError(f"Unknown policy: {name}")


def _rate(values: Any) -> float:
    items = list(values)
    return round(sum(bool(item) for item in items) / len(items), 4) if items else 0.0


def _write_results(
    *, source: Path, output_dir: Path, results: list[GatePolicyResult]
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_hash = sha256(source.read_bytes()).hexdigest()
    eligible = eligible_candidates(results)
    payload = {
        "source_report": str(source),
        "source_report_sha256": source_hash,
        "experiment_type": "offline_evidence_gate_replay",
        "retrieval_rerun": False,
        "results": [asdict(result) for result in results],
        "eligible_candidates": [asdict(result) for result in eligible],
    }
    (output_dir / "gate_calibration.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Evidence Gate Offline Calibration",
        "",
        f"- source report: `{source}`",
        f"- source SHA-256: `{source_hash}`",
        "- retrieval rerun: no",
        "",
        "| policy | parameters | full accept | partial boundary | none reject | macro accuracy |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            f"| {result.policy} | `{json.dumps(result.parameters)}` | "
            f"{result.full_acceptance_rate} | {result.partial_boundary_detection_rate} | "
            f"{result.none_rejection_rate} | {result.macro_accuracy} |"
        )
    lines.extend(["", "## Eligible candidates", ""])
    if eligible:
        for result in eligible:
            lines.append(
                f"- `{result.policy}` {result.parameters}: macro={result.macro_accuracy}, "
                f"full={result.full_acceptance_rate}, "
                f"partial={result.partial_boundary_detection_rate}, "
                f"none={result.none_rejection_rate}; "
                f"full losses={list(result.false_rejection_case_ids)}"
            )
    else:
        lines.append("No candidate passed the safety constraints.")
    (output_dir / "gate_calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay Evidence Gate policies offline.")
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.source_report.read_text(encoding="utf-8"))
    results = replay_report(report)
    _write_results(source=args.source_report, output_dir=args.output_dir, results=results)
    best = eligible_candidates(results)
    print(asdict(best[0]) if best else {"eligible_candidates": 0})


if __name__ == "__main__":
    main()

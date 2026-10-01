from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class UncertaintyRow:
    case_id: str
    recoverable_miss: bool
    answerability: str
    vector_top1_score: float
    vector_margin_1_2: float
    vector_span_1_6: float
    heading_vector_overlap_ratio: float
    top_heading_outside_vector: bool
    supplemental_heading_rank: int | None
    supplemental_heading_score: float
    demand_heading_overlap: float
    primary_gate_reject: bool


def extract_uncertainty_row(case: dict[str, Any]) -> UncertaintyRow:
    top_chunks = list(case.get("top_chunks") or [])
    vector_scores = [float(item.get("vector_score") or 0.0) for item in top_chunks]
    top1 = vector_scores[0] if vector_scores else 0.0
    top2 = vector_scores[1] if len(vector_scores) > 1 else top1
    top6 = (
        vector_scores[5] if len(vector_scores) > 5 else vector_scores[-1] if vector_scores else 0.0
    )

    stages = dict(case.get("retrieval_stages") or {})
    vector_ids = set(stages.get("vector_candidate_ids") or [])
    heading_ids = list(stages.get("heading_candidate_ids") or [])
    overlap_ratio = (
        len(vector_ids.intersection(heading_ids)) / len(heading_ids) if heading_ids else 0.0
    )
    supplemental = list(case.get("supplemental_chunks") or [])
    first_supplemental = supplemental[0] if supplemental else {}
    heading_text = " ".join(str(value) for value in first_supplemental.get("heading_path") or [])
    first_supplemental_rank = case.get("first_supplemental_rank")
    recoverable = bool(
        case.get("answerable")
        and case.get("first_relevant_rank") is None
        and first_supplemental_rank is not None
        and int(first_supplemental_rank) <= 1
    )
    return UncertaintyRow(
        case_id=str(case["id"]),
        recoverable_miss=recoverable,
        answerability=str(case["answerability"]),
        vector_top1_score=round(top1, 6),
        vector_margin_1_2=round(top1 - top2, 6),
        vector_span_1_6=round(top1 - top6, 6),
        heading_vector_overlap_ratio=round(overlap_ratio, 6),
        top_heading_outside_vector=bool(heading_ids and heading_ids[0] not in vector_ids),
        supplemental_heading_rank=(
            int(first_supplemental["heading_rank"])
            if first_supplemental.get("heading_rank") is not None
            else None
        ),
        supplemental_heading_score=float(first_supplemental.get("heading_score") or 0.0),
        demand_heading_overlap=round(
            _lexical_overlap(str(case.get("question") or ""), heading_text), 6
        ),
        primary_gate_reject=str(case.get("primary_evidence_decision")) == "none",
    )


def analyze_uncertainty(rows: list[UncertaintyRow]) -> dict[str, Any]:
    targets = [row.recoverable_miss for row in rows]
    numeric_features = (
        "vector_top1_score",
        "vector_margin_1_2",
        "vector_span_1_6",
        "heading_vector_overlap_ratio",
        "supplemental_heading_rank",
        "supplemental_heading_score",
        "demand_heading_overlap",
    )
    binary_features = ("top_heading_outside_vector", "primary_gate_reject")
    diagnostics: dict[str, Any] = {}
    for name in numeric_features:
        values = [float(getattr(row, name) or 0.0) for row in rows]
        diagnostics[name] = {
            "average_precision_high": _average_precision(values, targets, high=True),
            "average_precision_low": _average_precision(values, targets, high=False),
            "best_exploratory_rule": _best_threshold(values, targets),
        }
    for name in binary_features:
        predictions = [bool(getattr(row, name)) for row in rows]
        diagnostics[name] = _classification_metrics(predictions, targets)
    return {
        "total": len(rows),
        "recoverable_miss_count": sum(targets),
        "prevalence": round(sum(targets) / len(rows), 4) if rows else 0.0,
        "features": diagnostics,
        "two_feature_exploration": _best_two_feature_rules(rows),
        "recoverable_case_ids": [row.case_id for row in rows if row.recoverable_miss],
    }


def _best_two_feature_rules(rows: list[UncertaintyRow]) -> dict[str, dict[str, Any]]:
    """Development-only upper bounds for two preselected interpretable signals."""
    targets = [row.recoverable_miss for row in rows]
    overlap_values = [row.demand_heading_overlap for row in rows]
    score_values = [row.supplemental_heading_score for row in rows]
    best_by_operator: dict[str, dict[str, Any]] = {}
    for operator in ("and", "or"):
        best: dict[str, Any] = {"f1": 0.0, "precision": 0.0, "trigger_count": len(rows) + 1}
        for overlap_threshold in sorted(set(overlap_values)):
            for score_threshold in sorted(set(score_values)):
                overlap_hits = [value >= overlap_threshold for value in overlap_values]
                score_hits = [value >= score_threshold for value in score_values]
                predictions = [
                    left and right if operator == "and" else left or right
                    for left, right in zip(overlap_hits, score_hits, strict=True)
                ]
                metrics = _classification_metrics(predictions, targets)
                candidate = {
                    "operator": operator,
                    "overlap_threshold": overlap_threshold,
                    "heading_score_threshold": score_threshold,
                    **metrics,
                    "negative_trigger_count": sum(
                        prediction and row.answerability == "none"
                        for prediction, row in zip(predictions, rows, strict=True)
                    ),
                    "triggered_case_ids": [
                        row.case_id
                        for prediction, row in zip(predictions, rows, strict=True)
                        if prediction
                    ],
                }
                if (candidate["f1"], candidate["precision"], -candidate["trigger_count"]) > (
                    best["f1"],
                    best["precision"],
                    -best["trigger_count"],
                ):
                    best = candidate
        best_by_operator[operator] = best
    return best_by_operator


def _best_threshold(values: list[float], targets: list[bool]) -> dict[str, Any]:
    best: dict[str, Any] = {"f1": 0.0, "direction": "high", "threshold": 0.0}
    for threshold in sorted(set(values)):
        for direction in ("high", "low"):
            predictions = [
                value >= threshold if direction == "high" else value <= threshold
                for value in values
            ]
            metrics = _classification_metrics(predictions, targets)
            candidate = {"direction": direction, "threshold": threshold, **metrics}
            if (candidate["f1"], candidate["precision"], -candidate["trigger_count"]) > (
                best.get("f1", 0.0),
                best.get("precision", 0.0),
                -best.get("trigger_count", len(values) + 1),
            ):
                best = candidate
    return best


def _classification_metrics(predictions: list[bool], targets: list[bool]) -> dict[str, Any]:
    true_positive = sum(
        prediction and target for prediction, target in zip(predictions, targets, strict=True)
    )
    trigger_count = sum(predictions)
    target_count = sum(targets)
    precision = true_positive / trigger_count if trigger_count else 0.0
    recall = true_positive / target_count if target_count else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "trigger_count": trigger_count,
        "true_positive": true_positive,
        "false_positive": trigger_count - true_positive,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _average_precision(values: list[float], targets: list[bool], *, high: bool) -> float:
    ordered = sorted(
        zip(values, targets, strict=True),
        key=lambda item: item[0],
        reverse=high,
    )
    target_count = sum(targets)
    if not target_count:
        return 0.0
    hits = 0
    precision_sum = 0.0
    for rank, (_, target) in enumerate(ordered, start=1):
        if target:
            hits += 1
            precision_sum += hits / rank
    return round(precision_sum / target_count, 4)


def _lexical_overlap(query: str, heading: str) -> float:
    terms = _terms(query)
    if not terms:
        return 0.0
    lowered = heading.lower()
    return sum(term in lowered for term in terms) / len(terms)


def _terms(text: str) -> tuple[str, ...]:
    values: list[str] = []
    for token in re.findall(r"[a-zA-Z0-9_+#.-]{2,}", text.lower()):
        values.append(token)
    for segment in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        values.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    return tuple(dict.fromkeys(values))


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze heading-shadow trigger features.")
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    rows = [extract_uncertainty_row(case) for case in report["cases"]]
    result = {
        "source_report": str(args.report),
        "source_report_sha256": hashlib.sha256(args.report.read_bytes()).hexdigest(),
        "summary": analyze_uncertainty(rows),
        "rows": [asdict(row) for row in rows],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

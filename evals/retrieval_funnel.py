"""Build a compact retrieval-loss funnel from a retrieval evaluation report.

This module is diagnostic-only: it reads the stage data already emitted by the
eval runner and never invokes or changes retrieval, filtering, or Evidence Gate
behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def build_retrieval_funnel(report: dict[str, Any]) -> dict[str, Any]:
    """Separate counterfactual stage loss from mutually exclusive root cause."""
    cases = [case for case in report["cases"] if case.get("graded")]
    positives = [case for case in cases if case["answerability"] != "none"]
    negatives = [case for case in cases if case["answerability"] == "none"]
    top_k = int(report["metadata"]["retrieval_top_k"])
    candidate_k = int(report["metadata"]["retrieval_candidate_k"])

    candidate_hits = sum(case.get("first_raw_candidate_rank") is not None for case in positives)
    raw_top_k_hits = sum(
        (rank := case.get("first_raw_candidate_rank")) is not None and rank <= top_k
        for case in positives
    )
    filter_survivors = sum(
        case.get("first_post_filter_rank") is not None for case in positives
    )
    final_hits = sum(case.get("first_relevant_rank") is not None for case in positives)
    gate_accepts_after_hit = sum(
        case.get("first_relevant_rank") is not None and case.get("evidence_sufficient")
        for case in positives
    )

    terminal_losses = Counter(
        case.get("failure_category") or "success"
        for case in positives
        if case.get("failure_category") != "partial_answer_boundary"
    )
    terminal_losses["success"] += sum(
        case.get("failure_category") == "partial_answer_boundary" for case in positives
    )

    filter_exposure: Counter[str] = Counter()
    filter_terminal: Counter[str] = Counter()
    for case in positives:
        reasons = {
            item["reason"]
            for item in case.get("retrieval_stages", {}).get("filtered_out", [])
            if item.get("matched_ground_truth")
        }
        filter_exposure.update(reasons)
        category = str(case.get("failure_category") or "")
        if category.endswith("_filter_miss"):
            filter_terminal[category.removesuffix("_filter_miss")] += 1

    gate_by_answerability: dict[str, dict[str, int | float]] = {}
    for label in ("full", "partial"):
        rows = [case for case in positives if case["answerability"] == label]
        hit_rows = [case for case in rows if case.get("first_relevant_rank") is not None]
        accepted = sum(bool(case.get("evidence_sufficient")) for case in hit_rows)
        gate_by_answerability[label] = {
            "retrieval_hits": len(hit_rows),
            "accepted_after_hit": accepted,
            "acceptance_rate_after_hit": _rate(accepted, len(hit_rows)),
        }

    rejection_by_reason: dict[str, dict[str, int | float]] = {}
    grouped_negatives: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in negatives:
        grouped_negatives[str(case.get("negative_reason") or "unspecified")].append(case)
    for reason, rows in sorted(grouped_negatives.items()):
        rejected = sum(not case.get("evidence_sufficient") for case in rows)
        rejection_by_reason[reason] = {
            "total": len(rows),
            "rejected": rejected,
            "rejection_rate": _rate(rejected, len(rows)),
        }

    return {
        "source": {
            "dataset": report["dataset"],
            "dataset_sha256": report["metadata"]["dataset_sha256"],
            "git_commit": report["metadata"]["git_commit"],
            "experiment_mode": report["metadata"]["experiment_mode"],
            "top_k": top_k,
            "candidate_k": candidate_k,
            "max_chunks_per_document": report["metadata"].get(
                "retrieval_max_chunks_per_document"
            ),
        },
        "population": {
            "graded": len(cases),
            "answerable": len(positives),
            "negative": len(negatives),
        },
        "counterfactual_funnel": {
            f"candidate_hit_at_{candidate_k}": {
                "hits": candidate_hits,
                "rate": _rate(candidate_hits, len(positives)),
            },
            f"raw_rank_hit_at_{top_k}": {
                "hits": raw_top_k_hits,
                "rate": _rate(raw_top_k_hits, len(positives)),
            },
            "survived_diversity_filters_any_rank": {
                "hits": filter_survivors,
                "rate": _rate(filter_survivors, len(positives)),
            },
            f"final_hit_at_{top_k}": {
                "hits": final_hits,
                "rate": _rate(final_hits, len(positives)),
            },
            "gate_accept_after_final_hit": {
                "hits": gate_accepts_after_hit,
                "rate": _rate(gate_accepts_after_hit, final_hits),
                "denominator": final_hits,
            },
        },
        "counterfactual_losses": {
            "outside_candidate_pool": len(positives) - candidate_hits,
            "candidate_hit_but_raw_rank_below_top_k": candidate_hits - raw_top_k_hits,
            "candidate_hit_but_removed_by_filters": candidate_hits - filter_survivors,
            "survived_filters_but_below_final_top_k": filter_survivors - final_hits,
            "final_hit_but_gate_rejected": final_hits - gate_accepts_after_hit,
        },
        "mutually_exclusive_terminal_outcomes": dict(sorted(terminal_losses.items())),
        "filter_ground_truth_exposure": dict(sorted(filter_exposure.items())),
        "filter_terminal_losses": dict(sorted(filter_terminal.items())),
        "gate_after_retrieval_hit": gate_by_answerability,
        "negative_rejection_by_reason": rejection_by_reason,
    }


def render_markdown(funnel: dict[str, Any]) -> str:
    source = funnel["source"]
    population = funnel["population"]
    lines = [
        "# Development Retrieval Loss Funnel",
        "",
        "This is a diagnostic-only decomposition of one unchanged retrieval run.",
        "Counterfactual stage losses may overlap; terminal outcomes are mutually exclusive.",
        "",
        "## Reproducibility",
        "",
        f"- Dataset: `{source['dataset']}`",
        f"- Dataset SHA-256: `{source['dataset_sha256']}`",
        f"- Git commit: `{source['git_commit']}`",
        f"- Mode: `{source['experiment_mode']}`",
        f"- Top-K / candidate-K: `{source['top_k']}` / `{source['candidate_k']}`",
        f"- Per-document quota: `{source['max_chunks_per_document']}`",
        f"- Population: {population['graded']} graded; "
        f"{population['answerable']} answerable; {population['negative']} negative",
        "",
        "## Counterfactual funnel",
        "",
        "| Stage | Hits | Rate |",
        "| --- | ---: | ---: |",
    ]
    for stage, values in funnel["counterfactual_funnel"].items():
        lines.append(f"| {stage} | {values['hits']} | {values['rate']:.2%} |")

    lines.extend(
        [
            "",
            "## Counterfactual losses",
            "",
            "These counts answer separate what-if questions and therefore may overlap.",
            "",
            "| Loss | Cases |",
            "| --- | ---: |",
        ]
    )
    for loss, count in funnel["counterfactual_losses"].items():
        lines.append(f"| {loss} | {count} |")

    lines.extend(
        [
            "",
            "## Mutually exclusive terminal outcomes",
            "",
            "| Outcome | Cases |",
            "| --- | ---: |",
        ]
    )
    for outcome, count in funnel["mutually_exclusive_terminal_outcomes"].items():
        lines.append(f"| {outcome} | {count} |")

    lines.extend(
        [
            "",
            "## Ground-truth filter exposure",
            "",
            "| Filter reason | Any relevant chunk exposed | Terminal losses |",
            "| --- | ---: | ---: |",
        ]
    )
    reasons = set(funnel["filter_ground_truth_exposure"]) | set(
        funnel["filter_terminal_losses"]
    )
    for reason in sorted(reasons):
        lines.append(
            f"| {reason} | {funnel['filter_ground_truth_exposure'].get(reason, 0)} | "
            f"{funnel['filter_terminal_losses'].get(reason, 0)} |"
        )

    lines.extend(
        [
            "",
            "## Evidence Gate after a relevant retrieval hit",
            "",
            "| Answerability | Retrieval hits | Accepted | Acceptance rate |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for label, values in funnel["gate_after_retrieval_hit"].items():
        lines.append(
            f"| {label} | {values['retrieval_hits']} | {values['accepted_after_hit']} | "
            f"{values['acceptance_rate_after_hit']:.2%} |"
        )

    lines.extend(
        [
            "",
            "## Negative rejection by reason",
            "",
            "| Reason | Rejected / Total | Rate |",
            "| --- | ---: | ---: |",
        ]
    )
    for reason, values in funnel["negative_rejection_by_reason"].items():
        lines.append(
            f"| {reason} | {values['rejected']} / {values['total']} | "
            f"{values['rejection_rate']:.2%} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    raw = args.report.read_bytes()
    report = json.loads(raw)
    funnel = build_retrieval_funnel(report)
    funnel["generated_at"] = datetime.now(UTC).isoformat()
    funnel["source_report_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "retrieval_loss_funnel.json").write_text(
        json.dumps(funnel, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_dir / "retrieval_loss_funnel.md").write_text(
        render_markdown(funnel), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

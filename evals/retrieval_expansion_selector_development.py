"""Non-blind Development comparison for fixed@7 versus rank-capped@3 consumption."""

from __future__ import annotations

import argparse
import asyncio
import json
from hashlib import sha256
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import UUID

from agent_mentor.application.retrieval_expansion_budget import plan_retrieval_expansion_context
from agent_mentor.config import get_settings
from agent_mentor.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)
from agent_mentor.infrastructure.retriever import (
    CandidateExpansionStrategy,
    PostgresHybridRetriever,
)
from agent_mentor.ports.knowledge_retriever import RetrievalQuery
from evals.provenance import collect_git_state
from evals.retrieval_expansion_selector import select_rank_capped_supplemental
from evals.runners.retrieval_runner import _resolve_ground_truth
from evals.runners.runtime import create_embedding_gateway
from evals.schema import Answerability, load_dataset


def judge_selector(metrics: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    gates = thresholds["hard_gates"]
    checks = {
        key: passed
        for key, passed in {
            "primary_order_preservation": metrics["primary_order_preservation_rate"]
            >= gates["primary_order_preservation_rate_min"],
            "combined_recall": metrics["combined_recall"] >= gates["combined_recall_min"],
            "incremental_recovery": metrics["primary_miss_incremental_recovery_rate"]
            >= gates["primary_miss_incremental_recovery_rate_min"],
            "consumption_precision": metrics["supplemental_consumption_precision"]
            >= gates["supplemental_consumption_precision_min"],
            "average_consumed": metrics["average_consumed_supplemental_count"]
            <= gates["average_consumed_supplemental_count_max"],
            "overall_reduction": metrics["consumption_reduction_vs_fixed7"]
            >= gates["consumption_reduction_vs_fixed7_min"],
            "negative_average_consumed": metrics["negative_average_consumed_count"]
            <= gates["negative_average_consumed_count_max"],
            "negative_reduction": metrics["negative_consumption_reduction_vs_fixed7"]
            >= gates["negative_consumption_reduction_vs_fixed7_min"],
            "budget_compliance": metrics["budget_compliance_rate"]
            >= gates["budget_compliance_rate_min"],
        }.items()
    }
    return {"qualified": all(checks.values()), "checks": checks}


async def run_selector_development(
    *,
    positive_dataset: Path,
    negative_dataset: Path,
    thresholds_path: Path,
    knowledge_base_id: UUID,
    output_dir: Path,
) -> dict[str, Any]:
    thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
    cases = (
        *load_dataset(positive_dataset, require_graded=True).cases,
        *load_dataset(negative_dataset, require_graded=True).cases,
    )
    git = collect_git_state()
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    retriever = PostgresHybridRetriever(
        sessions,
        create_embedding_gateway(settings),
        max_chunks_per_document=settings.retrieval_max_chunks_per_document,
    )
    rows: list[dict[str, Any]] = []
    try:
        for case in cases:
            ground_truth, resolution = await _resolve_ground_truth(
                sessions, knowledge_base_id=knowledge_base_id, case=case
            )
            diagnostics = await retriever.retrieve_with_diagnostics(
                RetrievalQuery(knowledge_base_id, case.question, top_k=6, candidate_k=20),
                candidate_expansion=CandidateExpansionStrategy.HEADING_SHADOW,
            )
            fixed = plan_retrieval_expansion_context(
                diagnostics.final_results, diagnostics.supplemental_candidates
            )
            selected = select_rank_capped_supplemental(diagnostics.supplemental_candidates)
            capped = plan_retrieval_expansion_context(diagnostics.final_results, selected)
            relevant = set(ground_truth)
            primary_hit = any(item.chunk_id in relevant for item in diagnostics.final_results)
            combined_hit = any(item.chunk_id in relevant for item in capped.combined_chunks)
            rows.append(
                {
                    "case_id": case.case_id,
                    "answerability": case.answerability.value,
                    "ground_truth_resolution": resolution,
                    "primary_hit": primary_hit,
                    "combined_hit": combined_hit,
                    "primary_order_preserved": tuple(diagnostics.final_results)
                    == capped.combined_chunks[: len(diagnostics.final_results)],
                    "fixed_consumed_count": len(fixed.consumed_supplemental_chunks),
                    "selected_consumed_count": len(capped.consumed_supplemental_chunks),
                    "selected_relevant_count": sum(
                        item.chunk_id in relevant for item in capped.consumed_supplemental_chunks
                    ),
                    "budget_compliant": len(capped.combined_chunks) <= 13
                    and capped.supplemental_content_chars <= 7000
                    and capped.combined_content_chars <= 18000,
                }
            )
    finally:
        await engine.dispose()
    metrics = compute_selector_metrics(rows)
    qualification = judge_selector(metrics, thresholds)
    report = {
        "schema_version": "retrieval-expansion-selector-development-v1",
        "git": git.to_json(),
        "positive_dataset_sha256": _sha256(positive_dataset),
        "negative_dataset_sha256": _sha256(negative_dataset),
        "thresholds_sha256": _sha256(thresholds_path),
        "knowledge_base_id": str(knowledge_base_id),
        "metrics": metrics,
        "qualification": qualification,
        "cases": rows,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "qualification.json").write_text(
        json.dumps(qualification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def compute_selector_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    positives = [row for row in rows if row["answerability"] != Answerability.NONE.value]
    negatives = [row for row in rows if row["answerability"] == Answerability.NONE.value]
    primary_misses = [row for row in positives if not row["primary_hit"]]
    selected_total = sum(int(row["selected_consumed_count"]) for row in rows)
    fixed_total = sum(int(row["fixed_consumed_count"]) for row in rows)
    negative_selected = sum(int(row["selected_consumed_count"]) for row in negatives)
    negative_fixed = sum(int(row["fixed_consumed_count"]) for row in negatives)
    return {
        "case_count": len(rows),
        "combined_recall": _ratio(
            sum(bool(row["combined_hit"]) for row in positives), len(positives)
        ),
        "primary_miss_incremental_recovery_rate": _ratio(
            sum(bool(row["combined_hit"]) for row in primary_misses), len(primary_misses)
        ),
        "supplemental_consumption_precision": _ratio(
            sum(int(row["selected_relevant_count"]) for row in rows), selected_total
        ),
        "average_consumed_supplemental_count": round(
            mean(int(row["selected_consumed_count"]) for row in rows), 4
        ),
        "consumption_reduction_vs_fixed7": round(1 - selected_total / fixed_total, 4),
        "negative_average_consumed_count": round(
            mean(int(row["selected_consumed_count"]) for row in negatives), 4
        ),
        "negative_consumption_reduction_vs_fixed7": round(
            1 - negative_selected / negative_fixed, 4
        ),
        "primary_order_preservation_rate": _ratio(
            sum(bool(row["primary_order_preserved"]) for row in rows), len(rows)
        ),
        "budget_compliance_rate": _ratio(
            sum(bool(row["budget_compliant"]) for row in rows), len(rows)
        ),
    }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-base-id", type=UUID, required=True)
    parser.add_argument(
        "--positive-dataset",
        type=Path,
        default=Path("evals/datasets/retrieval_expansion_development_v1.jsonl"),
    )
    parser.add_argument(
        "--negative-dataset",
        type=Path,
        default=Path("evals/datasets/retrieval_expansion_selector_negatives_v1.jsonl"),
    )
    parser.add_argument(
        "--thresholds",
        type=Path,
        default=Path("evals/datasets/RETRIEVAL_EXPANSION_SELECTOR_DEVELOPMENT_THRESHOLDS.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evals/reports/retrieval_expansion_selector_development_v1"),
    )
    args = parser.parse_args()
    report = asyncio.run(
        run_selector_development(
            positive_dataset=args.positive_dataset,
            negative_dataset=args.negative_dataset,
            thresholds_path=args.thresholds,
            knowledge_base_id=args.knowledge_base_id,
            output_dir=args.output_dir,
        )
    )
    print(json.dumps(report["qualification"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

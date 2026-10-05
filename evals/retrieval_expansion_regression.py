"""Fixed candidate-only regression safety runner for retrieval expansion."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from statistics import mean
from time import perf_counter
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
    RetrievalExperimentMode,
)
from agent_mentor.ports.knowledge_retriever import RetrievalQuery, RetrievedChunk
from evals.provenance import collect_git_state
from evals.runners.retrieval_runner import (
    GROUND_TRUTH_ABSENT,
    GROUND_TRUTH_RESOLVED,
    _knowledge_base_fingerprint,
    _resolve_ground_truth,
)
from evals.runners.runtime import create_embedding_gateway
from evals.schema import Answerability, RetrievalEvalCase, load_dataset


def judge_regression(metrics: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    gates = thresholds["hard_gates"]
    checks = {
        "source_label_resolution": metrics["source_label_resolution_rate"]
        >= gates["source_label_resolution_rate_min"],
        "primary_top6_identity": metrics["primary_top6_identity_rate"]
        >= gates["primary_top6_identity_rate_min"],
        "primary_recall_delta": metrics["primary_recall_delta"]
        >= gates["primary_recall_delta_min"],
        "combined_recall_not_below_baseline": metrics["combined_recall"]
        >= metrics["baseline_primary_recall"],
        "negative_decision_unchanged": metrics["negative_decision_mutation_count"]
        <= gates["negative_decision_mutation_count_max"],
        "gate_not_invoked": metrics["gate_invocation_count"] <= gates["gate_invocation_count_max"],
        "generation_not_invoked": metrics["generation_invocation_count"]
        <= gates["generation_invocation_count_max"],
        "duplicate_free_combined": metrics["duplicate_free_combined_rate"]
        >= gates["duplicate_free_combined_rate_min"],
        "budget_compliance": metrics["budget_compliance_rate"]
        >= gates["budget_compliance_rate_min"],
        "average_consumed_count": metrics["average_consumed_supplemental_count"]
        <= gates["average_consumed_supplemental_count_max"],
        "supplemental_character_budget": metrics["max_supplemental_content_chars"]
        <= gates["max_supplemental_content_chars_max"],
        "combined_character_budget": metrics["max_combined_content_chars"]
        <= gates["max_combined_content_chars_max"],
        "supplemental_latency_p95": metrics["supplemental_latency_p95_ms"]
        <= gates["supplemental_latency_p95_ms_max"],
    }
    return {"qualified": all(checks.values()), "checks": checks}


async def run_regression(
    *,
    dataset_path: Path,
    thresholds_path: Path,
    knowledge_base_id: UUID,
    output_dir: Path,
) -> dict[str, Any]:
    cases = load_dataset(dataset_path, require_graded=True).cases
    thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
    config = thresholds["configuration"]
    git_state = collect_git_state()
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    retriever = PostgresHybridRetriever(
        sessions,
        create_embedding_gateway(settings),
        max_chunks_per_document=settings.retrieval_max_chunks_per_document,
    )
    rows: list[dict[str, Any]] = []
    started = perf_counter()
    try:
        fingerprint = await _knowledge_base_fingerprint(sessions, knowledge_base_id)
        for case in cases:
            rows.append(
                await _run_case(
                    case,
                    knowledge_base_id=knowledge_base_id,
                    sessions=sessions,
                    retriever=retriever,
                    top_k=int(config["primary_top_k"]),
                    candidate_k=int(config["candidate_k"]),
                )
            )
    finally:
        await engine.dispose()
    metrics = compute_regression_metrics(rows)
    qualification = judge_regression(metrics, thresholds)
    report = {
        "schema_version": "retrieval-expansion-regression-safety-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "git": git_state.to_json(),
        "dataset": str(dataset_path),
        "dataset_sha256": _sha256(dataset_path),
        "thresholds": str(thresholds_path),
        "thresholds_sha256": _sha256(thresholds_path),
        "knowledge_base_id": str(knowledge_base_id),
        "knowledge_base_fingerprint": fingerprint,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "configuration": config,
        "run_duration_ms": round((perf_counter() - started) * 1000, 4),
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


async def _run_case(
    case: RetrievalEvalCase,
    *,
    knowledge_base_id: UUID,
    sessions: Any,
    retriever: PostgresHybridRetriever,
    top_k: int,
    candidate_k: int,
) -> dict[str, Any]:
    ground_truth, resolution = await _resolve_ground_truth(
        sessions, knowledge_base_id=knowledge_base_id, case=case
    )
    query = RetrievalQuery(
        knowledge_base_id=knowledge_base_id,
        query=case.question,
        top_k=top_k,
        candidate_k=candidate_k,
    )
    baseline = await retriever.retrieve_with_diagnostics(
        query,
        experiment_mode=RetrievalExperimentMode.RRF_HEURISTIC,
        candidate_expansion=CandidateExpansionStrategy.NONE,
    )
    candidate_started = perf_counter()
    candidate = await retriever.retrieve_with_diagnostics(
        query,
        experiment_mode=RetrievalExperimentMode.RRF_HEURISTIC,
        candidate_expansion=CandidateExpansionStrategy.HEADING_SHADOW,
    )
    candidate_latency_ms = (perf_counter() - candidate_started) * 1000
    plan = plan_retrieval_expansion_context(
        candidate.final_results,
        candidate.supplemental_candidates,
    )
    relevant = set(ground_truth)
    baseline_ids = tuple(chunk.chunk_id for chunk in baseline.final_results)
    candidate_ids = tuple(chunk.chunk_id for chunk in candidate.final_results)
    combined_ids = tuple(chunk.chunk_id for chunk in plan.combined_chunks)
    is_negative = case.answerability is Answerability.NONE
    return {
        "case_id": case.case_id,
        "answerability": case.answerability.value,
        "ground_truth_resolution": resolution,
        "baseline_primary_chunk_ids": [str(item) for item in baseline_ids],
        "candidate_primary_chunk_ids": [str(item) for item in candidate_ids],
        "supplemental_candidate_chunk_ids": [
            str(chunk.chunk_id) for chunk in candidate.supplemental_candidates
        ],
        "consumed_supplemental_chunk_ids": [
            str(chunk.chunk_id) for chunk in plan.consumed_supplemental_chunks
        ],
        "combined_context_chunk_ids": [str(item) for item in combined_ids],
        "primary_identical": baseline_ids == candidate_ids,
        "baseline_primary_hit": _hit(baseline.final_results, relevant),
        "candidate_primary_hit": _hit(candidate.final_results, relevant),
        "combined_hit": _hit(plan.combined_chunks, relevant),
        "consumed_relevant_count": sum(
            chunk.chunk_id in relevant for chunk in plan.consumed_supplemental_chunks
        ),
        "duplicate_free_combined": len(combined_ids) == len(set(combined_ids)),
        "budget_compliant": (
            len(plan.consumed_supplemental_chunks) <= 7
            and len(plan.combined_chunks) <= 13
            and plan.supplemental_content_chars <= 7_000
            and plan.combined_content_chars <= 18_000
        ),
        "supplemental_candidate_count": len(candidate.supplemental_candidates),
        "consumed_supplemental_count": len(plan.consumed_supplemental_chunks),
        "supplemental_content_chars": plan.supplemental_content_chars,
        "combined_content_chars": plan.combined_content_chars,
        "supplemental_latency_ms": round(candidate_latency_ms, 4),
        "evaluation_mode": "negative_candidate_diagnostics_only" if is_negative else "positive",
        "evidence_decision_before": None,
        "evidence_decision_after": None,
        "gate_invoked": False,
        "generation_invoked": False,
    }


def compute_regression_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    positives = [row for row in rows if row["answerability"] != Answerability.NONE.value]
    negatives = [row for row in rows if row["answerability"] == Answerability.NONE.value]
    resolved = sum(
        row["ground_truth_resolution"] in {GROUND_TRUTH_RESOLVED, GROUND_TRUTH_ABSENT}
        for row in rows
    )
    baseline_hits = sum(bool(row["baseline_primary_hit"]) for row in positives)
    candidate_hits = sum(bool(row["candidate_primary_hit"]) for row in positives)
    combined_hits = sum(bool(row["combined_hit"]) for row in positives)
    primary_misses = [row for row in positives if not row["baseline_primary_hit"]]
    consumed = sum(int(row["consumed_supplemental_count"]) for row in rows)
    relevant_consumed = sum(int(row["consumed_relevant_count"]) for row in rows)
    latencies = sorted(float(row["supplemental_latency_ms"]) for row in rows)
    baseline_recall = _ratio(baseline_hits, len(positives))
    candidate_recall = _ratio(candidate_hits, len(positives))
    combined_recall = _ratio(combined_hits, len(positives))
    return {
        "case_count": len(rows),
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "source_label_resolution_rate": _ratio(resolved, len(rows)),
        "primary_top6_identity_rate": _ratio(
            sum(bool(row["primary_identical"]) for row in rows), len(rows)
        ),
        "baseline_primary_recall": baseline_recall,
        "candidate_primary_recall": candidate_recall,
        "primary_recall_delta": round(candidate_recall - baseline_recall, 4),
        "combined_recall": combined_recall,
        "combined_recall_gain": round(combined_recall - baseline_recall, 4),
        "primary_miss_incremental_recovery_rate": _ratio(
            sum(bool(row["combined_hit"]) for row in primary_misses), len(primary_misses)
        ),
        "supplemental_consumption_precision": _ratio(relevant_consumed, consumed),
        "negative_decision_mutation_count": sum(
            row["evidence_decision_before"] != row["evidence_decision_after"] for row in negatives
        ),
        "gate_invocation_count": sum(bool(row["gate_invoked"]) for row in rows),
        "generation_invocation_count": sum(bool(row["generation_invoked"]) for row in rows),
        "duplicate_free_combined_rate": _ratio(
            sum(bool(row["duplicate_free_combined"]) for row in rows), len(rows)
        ),
        "budget_compliance_rate": _ratio(
            sum(bool(row["budget_compliant"]) for row in rows), len(rows)
        ),
        "average_consumed_supplemental_count": round(
            mean(int(row["consumed_supplemental_count"]) for row in rows), 4
        ),
        "average_supplemental_content_chars": round(
            mean(int(row["supplemental_content_chars"]) for row in rows), 4
        ),
        "max_supplemental_content_chars": max(
            int(row["supplemental_content_chars"]) for row in rows
        ),
        "max_combined_content_chars": max(int(row["combined_content_chars"]) for row in rows),
        "supplemental_latency_p50_ms": _percentile(latencies, 0.50),
        "supplemental_latency_p95_ms": _percentile(latencies, 0.95),
        "negative_supplemental_candidate_count": sum(
            int(row["supplemental_candidate_count"]) for row in negatives
        ),
    }


def _hit(chunks: tuple[RetrievedChunk, ...], relevant: set[UUID]) -> bool:
    return bool(relevant) and any(chunk.chunk_id in relevant for chunk in chunks)


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    index = min(len(values) - 1, int((len(values) - 1) * quantile + 0.999999))
    return round(values[index], 4)


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=Path("evals/datasets/retrieval_regression_v1.jsonl")
    )
    parser.add_argument(
        "--thresholds",
        type=Path,
        default=Path("evals/datasets/RETRIEVAL_EXPANSION_REGRESSION_THRESHOLDS.json"),
    )
    parser.add_argument("--knowledge-base-id", type=UUID, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evals/reports/retrieval_expansion_regression_safety_v1"),
    )
    args = parser.parse_args()
    report = asyncio.run(
        run_regression(
            dataset_path=args.dataset,
            thresholds_path=args.thresholds,
            knowledge_base_id=args.knowledge_base_id,
            output_dir=args.output_dir,
        )
    )
    print(json.dumps(report["qualification"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Audit and run the non-blind second-stage retrieval Development fixture."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any
from uuid import UUID

from agent_mentor.config import get_settings
from agent_mentor.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)
from agent_mentor.infrastructure.retriever import PostgresHybridRetriever
from agent_mentor.ports.knowledge_retriever import RetrievalQuery
from agent_mentor.ports.supplemental_candidate_provider import SupplementalCandidateRequest
from evals.provenance import collect_git_state
from evals.retrieval_expansion_fixture import (
    HeadingShadowSupplementalProvider,
    RetrievalExpansionExecutionFixture,
)
from evals.runners.retrieval_runner import (
    GROUND_TRUTH_RESOLVED,
    _knowledge_base_fingerprint,
    _resolve_ground_truth,
)
from evals.runners.runtime import create_embedding_gateway
from evals.schema import LabelOrigin, RetrievalEvalCase, load_dataset

SCENARIOS = {
    "deep_heading_target",
    "semantic_paraphrase_target",
    "primary_coverage_control",
}


@dataclass(frozen=True, slots=True)
class ExpansionDevelopmentAudit:
    case_count: int
    scenario_counts: dict[str, int]
    case_ids: tuple[str, ...]


def audit_fixture(dataset_path: Path) -> ExpansionDevelopmentAudit:
    loaded = load_dataset(dataset_path, require_graded=True)
    raw_rows = _load_jsonl(dataset_path)
    if len(raw_rows) != len(loaded.cases):
        raise ValueError("raw and parsed fixture row counts disagree")
    if len(loaded.cases) != 12:
        raise ValueError("expansion Development fixture must contain exactly 12 cases")

    counts: Counter[str] = Counter()
    ids: list[str] = []
    questions: set[str] = set()
    for case, raw in zip(loaded.cases, raw_rows, strict=True):
        if case.split != "development" or case.label_origin is not LabelOrigin.HUMAN:
            raise ValueError(f"{case.case_id}: fixture must be human-labelled Development data")
        if not case.answerable or not case.relevant_sources:
            raise ValueError(f"{case.case_id}: fixture requires positive location labels")
        scenario = str(raw.get("expansion_scenario") or "")
        if scenario not in SCENARIOS:
            raise ValueError(f"{case.case_id}: unknown expansion_scenario {scenario!r}")
        if not str(raw.get("evaluation_intent") or "").strip():
            raise ValueError(f"{case.case_id}: evaluation_intent is required")
        if "retrieval_expansion_development" not in case.tags or scenario not in case.tags:
            raise ValueError(f"{case.case_id}: required fixture/scenario tags are missing")
        normalized_question = "".join(case.question.split()).casefold()
        if normalized_question in questions:
            raise ValueError(f"{case.case_id}: duplicate question")
        questions.add(normalized_question)
        ids.append(case.case_id)
        counts[scenario] += 1
    if set(counts) != SCENARIOS or set(counts.values()) != {4}:
        raise ValueError(f"fixture scenarios must be balanced 4/4/4, got {dict(counts)}")
    return ExpansionDevelopmentAudit(len(ids), dict(sorted(counts.items())), tuple(ids))


async def run_development(
    *,
    dataset_path: Path,
    thresholds_path: Path,
    knowledge_base_id: UUID,
    output_dir: Path,
) -> dict[str, Any]:
    audit = audit_fixture(dataset_path)
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
    provider = HeadingShadowSupplementalProvider(retriever)
    fixture = RetrievalExpansionExecutionFixture(provider, strategy=provider.strategy)
    rows: list[dict[str, Any]] = []
    started_at = perf_counter()
    try:
        fingerprint = await _knowledge_base_fingerprint(sessions, knowledge_base_id)
        for case in cases:
            rows.append(
                await _run_case(
                    case,
                    knowledge_base_id=knowledge_base_id,
                    sessions=sessions,
                    retriever=retriever,
                    fixture=fixture,
                    top_k=int(config["primary_top_k"]),
                    candidate_k=int(config["candidate_k"]),
                )
            )
    finally:
        await engine.dispose()

    metrics = _metrics(rows)
    qualification = _qualify(metrics, thresholds)
    report = {
        "schema_version": "retrieval-expansion-development-report-v1",
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
        "audit": asdict(audit),
        "run_duration_ms": round((perf_counter() - started_at) * 1000, 4),
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
    _write_summary(output_dir / "summary.md", report)
    return report


async def _run_case(
    case: RetrievalEvalCase,
    *,
    knowledge_base_id: UUID,
    sessions: Any,
    retriever: PostgresHybridRetriever,
    fixture: RetrievalExpansionExecutionFixture,
    top_k: int,
    candidate_k: int,
) -> dict[str, Any]:
    ground_truth, resolution = await _resolve_ground_truth(
        sessions, knowledge_base_id=knowledge_base_id, case=case
    )
    primary_started = perf_counter()
    primary = await retriever.retrieve(
        RetrievalQuery(
            knowledge_base_id=knowledge_base_id,
            query=case.question,
            top_k=top_k,
            candidate_k=candidate_k,
        )
    )
    primary_latency_ms = (perf_counter() - primary_started) * 1000
    execution = await fixture.execute(
        SupplementalCandidateRequest(
            knowledge_base_id=knowledge_base_id,
            question=case.question,
            candidate_k=candidate_k,
        ),
        primary=primary,
    )
    relevant = set(ground_truth)
    primary_hit = any(chunk.chunk_id in relevant for chunk in primary)
    candidate_hit = any(chunk.chunk_id in relevant for chunk in execution.candidates)
    consumed_relevant = [
        chunk.chunk_id
        for chunk in execution.plan.consumed_supplemental_chunks
        if chunk.chunk_id in relevant
    ]
    combined_hit = any(chunk.chunk_id in relevant for chunk in execution.plan.combined_chunks)
    combined_ids = [chunk.chunk_id for chunk in execution.plan.combined_chunks]
    primary_order_preserved = tuple(primary) == execution.plan.combined_chunks[: len(primary)]
    budget_compliant = (
        len(execution.plan.consumed_supplemental_chunks) <= 7
        and len(execution.plan.combined_chunks) <= 13
        and execution.plan.supplemental_content_chars <= 7_000
        and execution.plan.combined_content_chars <= 18_000
    )
    return {
        "case_id": case.case_id,
        "question": case.question,
        "scenario": next(tag for tag in case.tags if tag in SCENARIOS),
        "ground_truth_resolution": resolution,
        "ground_truth_chunk_ids": [str(item) for item in ground_truth],
        "primary_chunk_ids": [str(chunk.chunk_id) for chunk in primary],
        "supplemental_candidate_chunk_ids": [str(chunk.chunk_id) for chunk in execution.candidates],
        "consumed_supplemental_chunk_ids": [
            str(chunk.chunk_id) for chunk in execution.plan.consumed_supplemental_chunks
        ],
        "consumed_relevant_chunk_ids": [str(item) for item in consumed_relevant],
        "combined_context_chunk_ids": [str(item) for item in combined_ids],
        "deduplicated_chunk_ids": [str(item) for item in execution.trace.deduplicated_chunk_ids],
        "budget_rejected_chunk_ids": [
            str(item) for item in execution.trace.budget_rejected_chunk_ids
        ],
        "primary_hit": primary_hit,
        "supplemental_candidate_hit": candidate_hit,
        "combined_hit": combined_hit,
        "primary_order_preserved": primary_order_preserved,
        "duplicate_free_combined": len(combined_ids) == len(set(combined_ids)),
        "budget_compliant": budget_compliant,
        "primary_content_chars": execution.trace.primary_content_chars,
        "supplemental_content_chars": execution.trace.supplemental_content_chars,
        "combined_content_chars": execution.trace.combined_content_chars,
        "supplemental_candidate_count": len(execution.candidates),
        "consumed_supplemental_count": len(execution.plan.consumed_supplemental_chunks),
        "primary_latency_ms": round(primary_latency_ms, 4),
        "supplemental_latency_ms": round(execution.trace.retrieval_latency_ms, 4),
    }


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    resolved = sum(row["ground_truth_resolution"] == GROUND_TRUTH_RESOLVED for row in rows)
    primary_hits = sum(bool(row["primary_hit"]) for row in rows)
    combined_hits = sum(bool(row["combined_hit"]) for row in rows)
    primary_misses = [row for row in rows if not row["primary_hit"]]
    recovered = sum(bool(row["combined_hit"]) for row in primary_misses)
    consumed = sum(int(row["consumed_supplemental_count"]) for row in rows)
    relevant_consumed = sum(len(row["consumed_relevant_chunk_ids"]) for row in rows)
    latencies = sorted(float(row["supplemental_latency_ms"]) for row in rows)
    return {
        "case_count": total,
        "source_label_resolution_rate": _ratio(resolved, total),
        "primary_recall": _ratio(primary_hits, total),
        "combined_recall": _ratio(combined_hits, total),
        "combined_recall_gain": round(_ratio(combined_hits - primary_hits, total), 4),
        "primary_miss_count": len(primary_misses),
        "primary_miss_incremental_recovery_rate": _ratio(recovered, len(primary_misses)),
        "supplemental_candidate_recall_on_primary_miss": _ratio(
            sum(bool(row["supplemental_candidate_hit"]) for row in primary_misses),
            len(primary_misses),
        ),
        "supplemental_consumption_precision": _ratio(relevant_consumed, consumed),
        "primary_order_preservation_rate": _ratio(
            sum(bool(row["primary_order_preserved"]) for row in rows), total
        ),
        "duplicate_free_combined_rate": _ratio(
            sum(bool(row["duplicate_free_combined"]) for row in rows), total
        ),
        "budget_compliance_rate": _ratio(sum(bool(row["budget_compliant"]) for row in rows), total),
        "average_supplemental_candidate_count": round(
            mean(int(row["supplemental_candidate_count"]) for row in rows), 4
        ),
        "average_consumed_supplemental_count": round(
            mean(int(row["consumed_supplemental_count"]) for row in rows), 4
        ),
        "average_supplemental_content_chars": round(
            mean(int(row["supplemental_content_chars"]) for row in rows), 4
        ),
        "supplemental_latency_p50_ms": _percentile(latencies, 0.50),
        "supplemental_latency_p95_ms": _percentile(latencies, 0.95),
    }


def _qualify(metrics: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    hard = thresholds["hard_invariants"]
    development = thresholds["development_qualification"]
    checks = {
        "source_label_resolution": metrics["source_label_resolution_rate"]
        >= hard["source_label_resolution_rate_min"],
        "primary_order_preservation": metrics["primary_order_preservation_rate"]
        >= hard["primary_order_preservation_rate_min"],
        "duplicate_free_combined": metrics["duplicate_free_combined_rate"]
        >= hard["duplicate_free_combined_rate_min"],
        "budget_compliance": metrics["budget_compliance_rate"]
        >= hard["budget_compliance_rate_min"],
        "combined_recall_not_below_primary": metrics["combined_recall"]
        >= metrics["primary_recall"],
        "incremental_recovery": metrics["primary_miss_incremental_recovery_rate"]
        >= development["primary_miss_incremental_recovery_rate_min"],
        "consumption_precision": metrics["supplemental_consumption_precision"]
        >= development["supplemental_consumption_precision_min"],
        "combined_recall_gain": metrics["combined_recall_gain"]
        >= development["combined_recall_gain_min"],
        "average_consumed_count": metrics["average_consumed_supplemental_count"]
        <= development["average_consumed_supplemental_count_max"],
        "supplemental_latency_p95": metrics["supplemental_latency_p95_ms"]
        <= development["supplemental_latency_p95_ms_max"],
    }
    return {"qualified": all(checks.values()), "checks": checks}


def _write_summary(path: Path, report: dict[str, Any]) -> None:
    metrics = report["metrics"]
    qualification = report["qualification"]
    lines = [
        "# Retrieval Expansion Development Report",
        "",
        f"- Qualified: **{qualification['qualified']}**",
        f"- Dataset SHA-256: `{report['dataset_sha256']}`",
        f"- Primary recall: {metrics['primary_recall']}",
        f"- Combined recall: {metrics['combined_recall']}",
        f"- Combined recall gain: {metrics['combined_recall_gain']}",
        "- Primary-miss incremental recovery rate: "
        f"{metrics['primary_miss_incremental_recovery_rate']}",
        f"- Supplemental consumption precision: {metrics['supplemental_consumption_precision']}",
        f"- Average consumed supplemental chunks: {metrics['average_consumed_supplemental_count']}",
        "- Supplemental latency P50/P95 ms: "
        f"{metrics['supplemental_latency_p50_ms']} / {metrics['supplemental_latency_p95_ms']}",
        "",
        "## Qualification checks",
        "",
        *(f"- {name}: {passed}" for name, passed in qualification["checks"].items()),
        "",
        "This is non-blind Development evidence only. It does not authorize production, "
        "validation, or holdout.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("//")
    ]


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
        "--dataset",
        type=Path,
        default=Path("evals/datasets/retrieval_expansion_development_v1.jsonl"),
    )
    parser.add_argument(
        "--thresholds",
        type=Path,
        default=Path("evals/datasets/RETRIEVAL_EXPANSION_DEVELOPMENT_THRESHOLDS.json"),
    )
    parser.add_argument("--knowledge-base-id", type=UUID)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evals/reports/retrieval_expansion_development_v1"),
    )
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    audit = audit_fixture(args.dataset)
    if args.audit_only:
        print(json.dumps(asdict(audit), ensure_ascii=False, indent=2))
        return
    if args.knowledge_base_id is None:
        parser.error("--knowledge-base-id is required unless --audit-only is used")
    report = asyncio.run(
        run_development(
            dataset_path=args.dataset,
            thresholds_path=args.thresholds,
            knowledge_base_id=args.knowledge_base_id,
            output_dir=args.output_dir,
        )
    )
    print(json.dumps(report["qualification"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

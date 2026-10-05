"""Read-only candidate funnel for unrecovered retrieval-expansion Development cases."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
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
from agent_mentor.ports.knowledge_retriever import RetrievalQuery, RetrievedChunk
from evals.provenance import collect_git_state
from evals.runners.retrieval_runner import _resolve_ground_truth
from evals.runners.runtime import create_embedding_gateway
from evals.schema import load_dataset


def classify_funnel_loss(ranks: dict[str, int | None]) -> str:
    supplemental_rank = ranks["supplemental_rank"]
    if supplemental_rank is not None:
        return (
            "supplemental_budget_cutoff"
            if supplemental_rank > 7
            else "supplemental_should_have_recovered"
        )
    if ranks["heading_rank"] is not None and ranks["vector_rank"] is not None:
        return "heading_candidate_suppressed_by_vector_membership"
    if ranks["semantic_rank"] is not None:
        return "heading_lexical_gap_semantic_available"
    if ranks["vector_rank"] is not None or ranks["text_rank"] is not None:
        return "primary_ranking_miss_without_supplemental_route"
    return "candidate_recall_miss_all_routes"


async def run_funnel(
    *,
    dataset_path: Path,
    source_report_path: Path,
    knowledge_base_id: UUID,
    output_dir: Path,
) -> dict[str, Any]:
    source_report = json.loads(source_report_path.read_text(encoding="utf-8"))
    failed_ids = {row["case_id"] for row in source_report["cases"] if not bool(row["combined_hit"])}
    cases = [
        case
        for case in load_dataset(dataset_path, require_graded=True).cases
        if case.case_id in failed_ids
    ]
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
            query = RetrievalQuery(
                knowledge_base_id=knowledge_base_id,
                query=case.question,
                top_k=6,
                candidate_k=20,
            )
            heading = await retriever.retrieve_with_diagnostics(
                query,
                candidate_expansion=CandidateExpansionStrategy.HEADING_SHADOW,
            )
            semantic = await retriever.retrieve_with_diagnostics(
                query,
                candidate_expansion=CandidateExpansionStrategy.SEMANTIC_QUERY_SHADOW,
            )
            plan = plan_retrieval_expansion_context(
                heading.final_results,
                heading.supplemental_candidates,
            )
            relevant = set(ground_truth)
            ranks = {
                "vector_rank": _first_rank(heading.vector_candidates, relevant),
                "text_rank": _first_rank(heading.text_candidates, relevant),
                "ordered_rank": _first_rank(heading.ordered_candidates, relevant),
                "post_filter_rank": _first_rank(heading.post_filter_candidates, relevant),
                "primary_rank": _first_rank(heading.final_results, relevant),
                "heading_rank": _first_rank(heading.heading_candidates, relevant),
                "semantic_rank": _first_rank(semantic.semantic_candidates, relevant),
                "supplemental_rank": _first_rank(heading.supplemental_candidates, relevant),
                "consumed_rank": _first_rank(plan.consumed_supplemental_chunks, relevant),
            }
            rows.append(
                {
                    "case_id": case.case_id,
                    "question": case.question,
                    "ground_truth_resolution": resolution,
                    "ground_truth_chunk_ids": [str(item) for item in ground_truth],
                    "ranks": ranks,
                    "terminal_loss": classify_funnel_loss(ranks),
                    "heading_candidate_count": len(heading.heading_candidates),
                    "semantic_candidate_count": len(semantic.semantic_candidates),
                    "supplemental_candidate_count": len(heading.supplemental_candidates),
                    "consumed_supplemental_count": len(plan.consumed_supplemental_chunks),
                    "budget_rejected_count": len(plan.budget_rejected_chunk_ids),
                    "deduplicated_count": len(plan.deduplicated_chunk_ids),
                }
            )
    finally:
        await engine.dispose()

    loss_counts = Counter(row["terminal_loss"] for row in rows)
    report = {
        "schema_version": "retrieval-expansion-funnel-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "git": collect_git_state().to_json(),
        "scope": "read-only-unrecovered-development-cases",
        "source_report": str(source_report_path),
        "knowledge_base_id": str(knowledge_base_id),
        "case_count": len(rows),
        "terminal_loss_counts": dict(sorted(loss_counts.items())),
        "cases": rows,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "funnel.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "funnel.md").write_text(_render_markdown(report), encoding="utf-8")
    return report


def _first_rank(chunks: tuple[RetrievedChunk, ...], relevant: set[UUID]) -> int | None:
    return next(
        (rank for rank, chunk in enumerate(chunks, start=1) if chunk.chunk_id in relevant),
        None,
    )


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Retrieval Expansion Candidate Funnel",
        "",
        f"- Cases: {report['case_count']}",
        f"- Terminal losses: {report['terminal_loss_counts']}",
        "- Scope: read-only Development diagnostics; no algorithm or threshold changes.",
        "",
        "| Case | Vector | Text | Ordered | Heading | Semantic | Supplemental | Consumed | Loss |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report["cases"]:
        ranks = row["ranks"]
        lines.append(
            f"| {row['case_id']} | {_rank(ranks['vector_rank'])} | "
            f"{_rank(ranks['text_rank'])} | {_rank(ranks['ordered_rank'])} | "
            f"{_rank(ranks['heading_rank'])} | {_rank(ranks['semantic_rank'])} | "
            f"{_rank(ranks['supplemental_rank'])} | {_rank(ranks['consumed_rank'])} | "
            f"{row['terminal_loss']} |"
        )
    return "\n".join(lines) + "\n"


def _rank(value: object) -> str:
    return "-" if value is None else str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/datasets/retrieval_expansion_development_v1.jsonl"),
    )
    parser.add_argument(
        "--source-report",
        type=Path,
        default=Path("evals/reports/retrieval_expansion_development_v1/report.json"),
    )
    parser.add_argument("--knowledge-base-id", type=UUID, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evals/reports/retrieval_expansion_funnel_v1"),
    )
    args = parser.parse_args()
    report = asyncio.run(
        run_funnel(
            dataset_path=args.dataset,
            source_report_path=args.source_report,
            knowledge_base_id=args.knowledge_base_id,
            output_dir=args.output_dir,
        )
    )
    print(json.dumps(report["terminal_loss_counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

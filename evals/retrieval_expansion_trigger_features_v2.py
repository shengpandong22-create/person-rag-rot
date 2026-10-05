"""Read-only structural trigger features for supplemental consumption diagnostics."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import UUID

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
from evals.retrieval_trigger_features import structural_features
from evals.runners.retrieval_runner import _resolve_ground_truth
from evals.runners.runtime import create_embedding_gateway
from evals.schema import Answerability, load_dataset


def expansion_trigger_features(
    question: str,
    primary: tuple[RetrievedChunk, ...],
    supplemental: tuple[RetrievedChunk, ...],
) -> dict[str, Any]:
    primary_paths = {chunk.heading_path for chunk in primary}
    primary_documents = {chunk.document_logical_name or chunk.document_title for chunk in primary}
    supplemental_paths = [chunk.heading_path for chunk in supplemental]
    supplemental_documents = [
        chunk.document_logical_name or chunk.document_title for chunk in supplemental
    ]
    primary_heading_terms = _heading_terms(primary)
    supplemental_heading_terms = _heading_terms(supplemental)
    shared_terms = primary_heading_terms & supplemental_heading_terms
    structural = structural_features(
        {
            "question": question,
            "top_chunks": [_chunk_view(chunk) for chunk in primary],
            "supplemental_chunks": [_chunk_view(chunk) for chunk in supplemental],
        }
    )
    count = len(supplemental)
    return {
        "new_heading_path_ratio": _ratio(
            sum(path not in primary_paths for path in supplemental_paths), count
        ),
        "same_document_new_heading_ratio": _ratio(
            sum(
                document in primary_documents and path not in primary_paths
                for document, path in zip(supplemental_documents, supplemental_paths, strict=True)
            ),
            count,
        ),
        "new_document_ratio": _ratio(
            sum(document not in primary_documents for document in supplemental_documents), count
        ),
        "heading_concept_redundancy": _ratio(len(shared_terms), len(supplemental_heading_terms)),
        "heading_concept_novelty": _ratio(
            len(supplemental_heading_terms - primary_heading_terms),
            len(supplemental_heading_terms),
        ),
        "question_heading_novelty": structural["supplemental_novelty_ratio"],
        "primary_heading_coverage": structural["primary_heading_coverage"],
        "same_document_new_heading": structural["same_document_new_heading"],
        "primary_document_count": len(primary_documents),
        "supplemental_document_count": len(set(supplemental_documents)),
    }


async def run_feature_diagnostics(
    *,
    positive_dataset: Path,
    negative_dataset: Path,
    knowledge_base_id: UUID,
    output: Path,
) -> dict[str, Any]:
    cases = (
        *load_dataset(positive_dataset, require_graded=True).cases,
        *load_dataset(negative_dataset, require_graded=True).cases,
    )
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
            supplemental = diagnostics.supplemental_candidates[:3]
            relevant = set(ground_truth)
            primary_hit = any(chunk.chunk_id in relevant for chunk in diagnostics.final_results)
            supplemental_hit = any(chunk.chunk_id in relevant for chunk in supplemental)
            group = (
                "recoverable_positive"
                if case.answerability is not Answerability.NONE
                and not primary_hit
                and supplemental_hit
                else "hard_negative"
                if case.answerability is Answerability.NONE
                else "other_positive"
            )
            rows.append(
                {
                    "case_id": case.case_id,
                    "group": group,
                    "ground_truth_resolution": resolution,
                    "features": expansion_trigger_features(
                        case.question, diagnostics.final_results, supplemental
                    ),
                }
            )
    finally:
        await engine.dispose()
    report = {
        "schema_version": "retrieval-expansion-trigger-features-v2",
        "git": collect_git_state().to_json(),
        "scope": "read-only-feature-diagnostics-no-trigger-decision",
        "case_count": len(rows),
        "group_counts": dict(sorted(Counter(row["group"] for row in rows).items())),
        "group_feature_averages": _group_averages(rows),
        "cases": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _group_averages(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row["group"]), []).append(row["features"])
    return {
        group: {
            key: round(mean(float(item[key]) for item in items), 4)
            for key in items[0]
            if isinstance(items[0][key], (bool, int, float))
        }
        for group, items in sorted(groups.items())
    }


def _chunk_view(chunk: RetrievedChunk) -> dict[str, Any]:
    return {
        "document_logical_name": chunk.document_logical_name or chunk.document_title,
        "heading_path": list(chunk.heading_path),
    }


def _heading_terms(chunks: tuple[RetrievedChunk, ...]) -> set[str]:
    return {
        part.casefold()
        for chunk in chunks
        for heading in chunk.heading_path
        for part in heading.replace("：", " ").replace("——", " ").split()
        if len(part) >= 2
    }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


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
        "--output",
        type=Path,
        default=Path("evals/reports/retrieval_expansion_trigger_features_v2/report.json"),
    )
    args = parser.parse_args()
    report = asyncio.run(
        run_feature_diagnostics(
            positive_dataset=args.positive_dataset,
            negative_dataset=args.negative_dataset,
            knowledge_base_id=args.knowledge_base_id,
            output=args.output,
        )
    )
    print(json.dumps(report["group_feature_averages"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

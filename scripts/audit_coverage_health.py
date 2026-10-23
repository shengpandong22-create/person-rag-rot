"""Read-only health audit for the knowledge catalog and interview coverage loop.

This script never writes catalog rows, interview rows, or user profile data.  It
is deliberately separate from reindexing so an existing user knowledge base can
be assessed before anyone decides to rebuild its catalog.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from uuid import UUID

from sqlalchemy import case, func, select

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from agent_mentor.application.coverage_catalog import classify_catalog_candidate  # noqa: E402
from agent_mentor.config import get_settings  # noqa: E402
from agent_mentor.infrastructure.database.models import (  # noqa: E402
    EvaluationModel,
    InterviewQuestionModel,
    InterviewSessionModel,
    KnowledgeCatalogPointModel,
    KnowledgeCatalogSourceModel,
    KnowledgeChunkModel,
    QuestionCoverageModel,
    QuestionReferenceModel,
)
from agent_mentor.infrastructure.database.session import (  # noqa: E402
    create_database_engine,
    create_session_factory,
)


async def audit(knowledge_base_id: UUID) -> dict[str, object]:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as db:
            source_rows = (
                await db.execute(
                    select(
                        KnowledgeCatalogPointModel.id,
                        KnowledgeCatalogPointModel.title,
                        KnowledgeChunkModel.heading_path,
                        KnowledgeChunkModel.content,
                    )
                    .join(
                        KnowledgeCatalogSourceModel,
                        KnowledgeCatalogSourceModel.knowledge_point_id
                        == KnowledgeCatalogPointModel.id,
                    )
                    .join(
                        KnowledgeChunkModel,
                        KnowledgeChunkModel.id == KnowledgeCatalogSourceModel.chunk_id,
                    )
                    .where(KnowledgeCatalogPointModel.knowledge_base_id == knowledge_base_id)
                    .order_by(KnowledgeCatalogPointModel.title, KnowledgeChunkModel.chunk_index)
                )
            ).all()

            point_sources: dict[UUID, dict[str, object]] = {}
            decision_counts: Counter[str] = Counter()
            for point_id, title, heading_path, content in source_rows:
                candidate = classify_catalog_candidate(list(heading_path), content)
                decision_counts[candidate.decision] += 1
                point = point_sources.setdefault(
                    point_id,
                    {"title": title, "sources": [], "decisions": []},
                )
                point["sources"].append(
                    {
                        "heading_path": heading_path,
                        "candidate_title": candidate.title,
                        "decision": candidate.decision,
                    }
                )
                point["decisions"].append(candidate.decision)

            coverage_rows = (
                await db.execute(
                    select(
                        QuestionCoverageModel.knowledge_point_id,
                        func.count(func.distinct(QuestionCoverageModel.question_id)).label("attempt_count"),
                        func.count(
                            func.distinct(
                                case(
                                    (
                                        (EvaluationModel.status == "final")
                                        & (EvaluationModel.confidence >= 0.70),
                                        EvaluationModel.id,
                                    ),
                                )
                            )
                        ).label("trusted_evaluation_count"),
                    )
                    .join(
                        InterviewQuestionModel,
                        InterviewQuestionModel.id == QuestionCoverageModel.question_id,
                    )
                    .join(
                        InterviewSessionModel,
                        InterviewSessionModel.id == InterviewQuestionModel.session_id,
                    )
                    .outerjoin(
                        EvaluationModel,
                        EvaluationModel.question_id == InterviewQuestionModel.id,
                    )
                    .where(InterviewSessionModel.knowledge_base_id == knowledge_base_id)
                    .group_by(QuestionCoverageModel.knowledge_point_id)
                )
            ).all()
            coverage_by_point = {
                point_id: {"attempt_count": int(attempts), "trusted_evaluation_count": int(trusted)}
                for point_id, attempts, trusted in coverage_rows
            }

            provenance_rows = (
                await db.execute(
                    select(
                        QuestionCoverageModel.knowledge_point_id,
                        QuestionCoverageModel.question_id,
                        func.bool_or(
                            QuestionReferenceModel.chunk_id == KnowledgeCatalogSourceModel.chunk_id
                        ).label("has_cited_source"),
                    )
                    .join(
                        InterviewQuestionModel,
                        InterviewQuestionModel.id == QuestionCoverageModel.question_id,
                    )
                    .join(
                        InterviewSessionModel,
                        InterviewSessionModel.id == InterviewQuestionModel.session_id,
                    )
                    .outerjoin(
                        QuestionReferenceModel,
                        QuestionReferenceModel.question_id == QuestionCoverageModel.question_id,
                    )
                    .outerjoin(
                        KnowledgeCatalogSourceModel,
                        KnowledgeCatalogSourceModel.knowledge_point_id
                        == QuestionCoverageModel.knowledge_point_id,
                    )
                    .where(InterviewSessionModel.knowledge_base_id == knowledge_base_id)
                    .group_by(
                        QuestionCoverageModel.knowledge_point_id,
                        QuestionCoverageModel.question_id,
                    )
                )
            ).all()
            provenance_mismatch = [
                {"point_id": str(point_id), "question_id": str(question_id)}
                for point_id, question_id, has_cited_source in provenance_rows
                if has_cited_source is False
            ]
            provenance_missing_reference = [
                {"point_id": str(point_id), "question_id": str(question_id)}
                for point_id, question_id, has_cited_source in provenance_rows
                if has_cited_source is None
            ]

            points: list[dict[str, object]] = []
            for point_id, detail in point_sources.items():
                decisions = detail["decisions"]
                assert isinstance(decisions, list)
                all_accepted = all(item.startswith("accepted_") for item in decisions)
                quality = "qualified" if all_accepted else "review"
                counts = coverage_by_point.get(
                    point_id, {"attempt_count": 0, "trusted_evaluation_count": 0}
                )
                points.append(
                    {
                        "id": str(point_id),
                        "title": detail["title"],
                        "quality": quality,
                        **counts,
                        "source_count": len(detail["sources"]),
                        "source_decisions": sorted(set(decisions)),
                    }
                )
            points.sort(key=lambda item: (str(item["quality"]), str(item["title"])))
            qualified_uncovered = sum(
                item["quality"] == "qualified" and item["attempt_count"] == 0 for item in points
            )
            return {
                "script": "scripts/audit_coverage_health.py",
                "write_behavior": "read_only",
                "knowledge_base_id": str(knowledge_base_id),
                "total_catalog_points": len(points),
                "qualified_catalog_points": sum(
                    item["quality"] == "qualified" for item in points
                ),
                "review_required_catalog_points": sum(
                    item["quality"] == "review" for item in points
                ),
                "qualified_uncovered_points": qualified_uncovered,
                "current_three_question_rounds_to_visit_each_qualified_gap": qualified_uncovered,
                "catalog_source_decisions": dict(sorted(decision_counts.items())),
                "coverage_mappings": len(provenance_rows),
                "provenance_verified_coverage_mappings": sum(
                    has_cited_source is True
                    for _, _, has_cited_source in provenance_rows
                ),
                "provenance_mismatch_coverage_mappings": len(provenance_mismatch),
                "provenance_missing_reference_coverage_mappings": len(
                    provenance_missing_reference
                ),
                "untrusted_historical_coverage_mappings": len(provenance_mismatch)
                + len(provenance_missing_reference),
                "provenance_mismatch_samples": provenance_mismatch[:20],
                "provenance_missing_reference_samples": provenance_missing_reference[:20],
                "points": points,
            }
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("knowledge_base_id", type=UUID)
    parser.add_argument("--output", type=Path, help="Optional JSON report destination.")
    args = parser.parse_args()
    result = asyncio.run(audit(args.knowledge_base_id))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()

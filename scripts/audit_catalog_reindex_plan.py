"""Produce a read-only, per-document catalog reindex diff.

The output is a review artifact, not a migration command.  It compares active
chunks classified by today's production catalog rule with existing source links;
it never inserts, deletes, or updates a database row.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from agent_mentor.application.coverage_catalog import (  # noqa: E402
    CatalogCandidate,
    classify_catalog_candidate,
)
from agent_mentor.config import get_settings  # noqa: E402
from agent_mentor.infrastructure.database.models import (  # noqa: E402
    KnowledgeCatalogPointModel,
    KnowledgeCatalogSourceModel,
    KnowledgeChunkModel,
    SourceDocumentModel,
)
from agent_mentor.infrastructure.database.session import (  # noqa: E402
    create_database_engine,
    create_session_factory,
)


def document_diff(
    *,
    existing_titles: set[str],
    candidates: list[CatalogCandidate],
) -> dict[str, object]:
    """Calculate a deterministic review diff without database dependencies."""
    accepted_titles = {candidate.title for candidate in candidates if candidate.title is not None}
    decisions: dict[str, int] = defaultdict(int)
    for candidate in candidates:
        decisions[candidate.decision] += 1
    return {
        "existing_titles": sorted(existing_titles),
        "candidate_titles": sorted(accepted_titles),
        "would_add_titles": sorted(accepted_titles - existing_titles),
        "would_unlink_titles": sorted(existing_titles - accepted_titles),
        "candidate_decisions": dict(sorted(decisions.items())),
    }


async def audit(knowledge_base_id: UUID) -> dict[str, object]:
    engine = create_database_engine(get_settings().database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as db:
            documents = list(
                (
                    await db.scalars(
                        select(SourceDocumentModel)
                        .where(
                            SourceDocumentModel.knowledge_base_id == knowledge_base_id,
                            SourceDocumentModel.is_active.is_(True),
                        )
                        .order_by(SourceDocumentModel.original_filename)
                    )
                ).all()
            )
            existing_rows = (
                await db.execute(
                    select(
                        KnowledgeCatalogSourceModel.document_id,
                        KnowledgeCatalogPointModel.title,
                    )
                    .join(
                        KnowledgeCatalogPointModel,
                        KnowledgeCatalogPointModel.id
                        == KnowledgeCatalogSourceModel.knowledge_point_id,
                    )
                    .where(KnowledgeCatalogPointModel.knowledge_base_id == knowledge_base_id)
                )
            ).all()
            existing_by_document: dict[UUID, set[str]] = defaultdict(set)
            for document_id, title in existing_rows:
                existing_by_document[document_id].add(title)

            rows: list[dict[str, object]] = []
            for document in documents:
                chunks = list(
                    (
                        await db.scalars(
                            select(KnowledgeChunkModel)
                            .where(
                                KnowledgeChunkModel.document_id == document.id,
                                KnowledgeChunkModel.is_active.is_(True),
                            )
                            .order_by(KnowledgeChunkModel.chunk_index)
                        )
                    ).all()
                )
                nested = any(len(chunk.heading_path) > 1 for chunk in chunks)
                inspected: list[dict[str, object]] = []
                candidates: list[CatalogCandidate] = []
                for chunk in chunks:
                    candidate = (
                        CatalogCandidate(None, "rejected_container_heading")
                        if nested and len(chunk.heading_path) <= 1
                        else classify_catalog_candidate(chunk.heading_path, chunk.content)
                    )
                    candidates.append(candidate)
                    inspected.append(
                        {
                            "chunk_id": str(chunk.id),
                            "chunk_index": chunk.chunk_index,
                            "heading_path": chunk.heading_path,
                            "candidate_title": candidate.title,
                            "decision": candidate.decision,
                        }
                    )
                diff = document_diff(
                    existing_titles=existing_by_document.get(document.id, set()),
                    candidates=candidates,
                )
                rows.append(
                    {
                        "document_id": str(document.id),
                        "logical_name": document.logical_name,
                        "original_filename": document.original_filename,
                        "content_hash": document.content_hash,
                        "status": str(document.status),
                        "active_chunk_count": len(chunks),
                        **diff,
                        "chunks": inspected,
                    }
                )
            source_backed_points = set(
                value for values in existing_by_document.values() for value in values
            )
            all_points = set(
                (
                    await db.scalars(
                        select(KnowledgeCatalogPointModel.title).where(
                            KnowledgeCatalogPointModel.knowledge_base_id == knowledge_base_id
                        )
                    )
                ).all()
            )
            return {
                "script": "scripts/audit_catalog_reindex_plan.py",
                "write_behavior": "read_only",
                "knowledge_base_id": str(knowledge_base_id),
                "document_count": len(rows),
                "orphan_catalog_point_titles": sorted(all_points - source_backed_points),
                "documents": rows,
                "summary": {
                    "would_add_title_count": sum(len(row["would_add_titles"]) for row in rows),
                    "would_unlink_title_count": sum(
                        len(row["would_unlink_titles"]) for row in rows
                    ),
                    "orphan_catalog_point_count": len(all_points - source_backed_points),
                },
            }
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("knowledge_base_id", type=UUID)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(audit(args.knowledge_base_id))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()

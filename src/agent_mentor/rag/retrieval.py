from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from agent_mentor.ports.knowledge_retriever import RetrievedChunk


def normalize_query(query: str) -> str:
    """Normalize spacing while preserving Java names, acronyms, and exception names."""
    return re.sub(r"\s+", " ", query).strip()


def reciprocal_rank_fusion(ranked_lists: list[list[UUID]], *, rrf_k: int = 60) -> dict[UUID, float]:
    scores: dict[UUID, float] = {}
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
    return scores


def validate_citations(citation_ids: list[UUID], context: list[RetrievedChunk]) -> None:
    allowed = {chunk.chunk_id for chunk in context}
    invalid = [chunk_id for chunk_id in citation_ids if chunk_id not in allowed]
    if invalid:
        joined = ", ".join(str(chunk_id) for chunk_id in invalid)
        raise ValueError(f"Citations are not in the current retrieval context: {joined}")


@dataclass(frozen=True, slots=True)
class EvidenceContext:
    chunks: tuple[RetrievedChunk, ...]

    def render_for_prompt(self) -> str:
        blocks: list[str] = []
        for index, chunk in enumerate(self.chunks, start=1):
            location = " > ".join(chunk.heading_path)
            if chunk.page_number is not None:
                location = (
                    f"{location} p.{chunk.page_number}" if location else f"p.{chunk.page_number}"
                )
            blocks.append(
                "\n".join(
                    [
                        f"[{index}] chunk_id={chunk.chunk_id}",
                        f"title={chunk.document_title}",
                        f"location={location or 'unknown'}",
                        f"trust_level={chunk.trust_level}",
                        f"content={chunk.content}",
                    ]
                )
            )
        return "\n\n".join(blocks)

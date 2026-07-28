from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from agent_mentor.domain.knowledge import TrustLevel


class RetrievalMode(StrEnum):
    VECTOR = "vector"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    knowledge_base_id: UUID
    query: str
    top_k: int = 6
    candidate_k: int = 20
    mode: RetrievalMode = RetrievalMode.HYBRID
    trust_levels: tuple[TrustLevel, ...] | None = None


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    source_url: str | None
    trust_level: str
    heading_path: tuple[str, ...]
    page_number: int | None
    block_type: str
    chunk_index: int
    content: str
    score: float
    retrieval_explanation: str
    vector_rank: int | None = None
    text_rank: int | None = None
    vector_score: float | None = None
    text_score: float | None = None


class KnowledgeRetriever(Protocol):
    async def retrieve(self, query: RetrievalQuery) -> list[RetrievedChunk]: ...

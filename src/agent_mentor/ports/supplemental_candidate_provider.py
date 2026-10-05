"""Port for explicitly requested, non-primary retrieval candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from agent_mentor.ports.knowledge_retriever import RetrievedChunk


@dataclass(frozen=True, slots=True)
class SupplementalCandidateRequest:
    knowledge_base_id: UUID
    question: str
    candidate_k: int = 20


class SupplementalCandidateProvider(Protocol):
    async def candidates(
        self, request: SupplementalCandidateRequest
    ) -> tuple[RetrievedChunk, ...]: ...

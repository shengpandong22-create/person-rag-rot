"""Feature-gated orchestration skeleton for user-triggered retrieval expansion.

This module intentionally does not call a retriever. It owns only parent validation,
one-shot/idempotency semantics, and creation of the persistent expansion claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from agent_mentor.api.errors import AppError


class RetrievalExpansionTrigger(StrEnum):
    USER_REQUESTED_MORE_EVIDENCE = "user_requested_more_evidence"


class RetrievalExpansionStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ExpansionParentContext:
    knowledge_base_id: UUID
    session_id: UUID
    parent_message_id: UUID
    role: str
    question: str | None
    allow_model_knowledge: bool | None
    primary_chunk_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class RetrievalExpansionRecord:
    expansion_id: UUID
    parent_message_id: UUID
    idempotency_key: UUID
    trigger: RetrievalExpansionTrigger
    status: RetrievalExpansionStatus
    result_message_id: UUID | None = None


class RetrievalExpansionRepository(Protocol):
    async def parent_context(self, parent_message_id: UUID) -> ExpansionParentContext | None: ...

    async def by_parent(self, parent_message_id: UUID) -> RetrievalExpansionRecord | None: ...

    async def claim(self, record: RetrievalExpansionRecord) -> RetrievalExpansionRecord: ...


class RetrievalExpansionClaimConflict(Exception):
    """The database unique constraint was won by a concurrent request."""


class RetrievalExpansionService:
    """Validate and claim an expansion without executing supplemental retrieval."""

    def __init__(
        self,
        repository: RetrievalExpansionRepository,
        *,
        enabled: bool = False,
    ) -> None:
        self._repository = repository
        self._enabled = enabled

    async def start(
        self,
        *,
        knowledge_base_id: UUID,
        parent_message_id: UUID,
        idempotency_key: UUID,
        trigger: RetrievalExpansionTrigger,
    ) -> RetrievalExpansionRecord:
        if not self._enabled:
            raise AppError(
                "RETRIEVAL_EXPANSION_DISABLED",
                "Retrieval expansion is not enabled.",
                status_code=404,
            )
        parent = await self._repository.parent_context(parent_message_id)
        if parent is None or parent.knowledge_base_id != knowledge_base_id:
            raise AppError(
                "PARENT_ANSWER_NOT_FOUND",
                "Parent answer was not found.",
                status_code=404,
            )
        if parent.role != "assistant":
            raise AppError(
                "PARENT_MESSAGE_NOT_ASSISTANT",
                "Parent message must be an assistant answer.",
                status_code=422,
            )
        if parent.question is None or parent.allow_model_knowledge is None:
            raise AppError(
                "PARENT_CONTEXT_UNAVAILABLE",
                "Parent retrieval context is unavailable.",
                status_code=422,
            )
        if len(parent.primary_chunk_ids) > 6:
            raise AppError(
                "PARENT_CONTEXT_UNAVAILABLE",
                "Parent retrieval context exceeds the v1 primary budget.",
                status_code=422,
            )

        existing = await self._repository.by_parent(parent_message_id)
        if existing is not None:
            return self._resolve_existing(existing, idempotency_key)

        record = RetrievalExpansionRecord(
            expansion_id=uuid4(),
            parent_message_id=parent_message_id,
            idempotency_key=idempotency_key,
            trigger=trigger,
            status=RetrievalExpansionStatus.STARTED,
        )
        try:
            return await self._repository.claim(record)
        except RetrievalExpansionClaimConflict:
            winner = await self._repository.by_parent(parent_message_id)
            if winner is None:
                raise AppError(
                    "EXPANSION_IN_PROGRESS",
                    "Retrieval expansion is being claimed.",
                    status_code=409,
                ) from None
            return self._resolve_existing(winner, idempotency_key)

    @staticmethod
    def _resolve_existing(
        existing: RetrievalExpansionRecord, idempotency_key: UUID
    ) -> RetrievalExpansionRecord:
        if (
            existing.idempotency_key == idempotency_key
            and existing.status is RetrievalExpansionStatus.COMPLETED
        ):
            return existing
        code = (
            "EXPANSION_IN_PROGRESS"
            if existing.status is RetrievalExpansionStatus.STARTED
            else "EXPANSION_ALREADY_EXISTS"
        )
        raise AppError(code, "Retrieval expansion already exists.", status_code=409)

"""SQLAlchemy persistence adapter for retrieval expansion orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.application.retrieval_expansion_service import (
    ExpansionParentContext,
    RetrievalExpansionClaimConflict,
    RetrievalExpansionRecord,
    RetrievalExpansionStatus,
    RetrievalExpansionTrigger,
)
from agent_mentor.infrastructure.database.models import (
    ChatMessageModel,
    ChatRetrievalExpansionModel,
    ChatSessionModel,
)


class SqlAlchemyRetrievalExpansionRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def parent_context(self, parent_message_id: UUID) -> ExpansionParentContext | None:
        async with self._sessions() as session:
            result = await session.execute(
                select(ChatMessageModel, ChatSessionModel)
                .join(ChatSessionModel, ChatSessionModel.id == ChatMessageModel.session_id)
                .where(ChatMessageModel.id == parent_message_id)
            )
            row = result.one_or_none()
            if row is None:
                return None
            message, chat_session = row
            question = await session.scalar(
                select(ChatMessageModel.content)
                .where(
                    ChatMessageModel.session_id == message.session_id,
                    ChatMessageModel.role == "user",
                    ChatMessageModel.created_at <= message.created_at,
                )
                .order_by(ChatMessageModel.created_at.desc())
                .limit(1)
            )

        diagnostics = message.retrieval_diagnostics
        return ExpansionParentContext(
            knowledge_base_id=chat_session.knowledge_base_id,
            session_id=message.session_id,
            parent_message_id=message.id,
            role=message.role,
            question=question,
            allow_model_knowledge=_boolean_field(diagnostics, "allow_model_knowledge"),
            primary_chunk_ids=_primary_chunk_ids(diagnostics),
        )

    async def by_parent(self, parent_message_id: UUID) -> RetrievalExpansionRecord | None:
        async with self._sessions() as session:
            model = await session.scalar(
                select(ChatRetrievalExpansionModel).where(
                    ChatRetrievalExpansionModel.parent_message_id == parent_message_id
                )
            )
        return _to_record(model) if model is not None else None

    async def claim(self, record: RetrievalExpansionRecord) -> RetrievalExpansionRecord:
        model = ChatRetrievalExpansionModel(
            id=record.expansion_id,
            parent_message_id=record.parent_message_id,
            result_message_id=record.result_message_id,
            idempotency_key=record.idempotency_key,
            trigger=record.trigger.value,
            status=record.status.value,
            request_snapshot={},
            trace={},
        )
        async with self._sessions() as session:
            session.add(model)
            try:
                await session.commit()
            except IntegrityError as error:
                await session.rollback()
                raise RetrievalExpansionClaimConflict from error
        return record


def _to_record(model: ChatRetrievalExpansionModel) -> RetrievalExpansionRecord:
    return RetrievalExpansionRecord(
        expansion_id=model.id,
        parent_message_id=model.parent_message_id,
        idempotency_key=model.idempotency_key,
        trigger=RetrievalExpansionTrigger(model.trigger),
        status=RetrievalExpansionStatus(model.status),
        result_message_id=model.result_message_id,
    )


def _boolean_field(diagnostics: object, key: str) -> bool | None:
    if not isinstance(diagnostics, Mapping):
        return None
    value = diagnostics.get(key)
    return value if isinstance(value, bool) else None


def _primary_chunk_ids(diagnostics: object) -> tuple[UUID, ...]:
    if not isinstance(diagnostics, Mapping):
        return ()
    candidates = diagnostics.get("candidates")
    if not isinstance(candidates, list):
        return ()

    parsed: list[UUID] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            return ()
        value: Any = candidate.get("chunk_id")
        try:
            parsed.append(UUID(str(value)))
        except (TypeError, ValueError, AttributeError):
            return ()
    return tuple(parsed)

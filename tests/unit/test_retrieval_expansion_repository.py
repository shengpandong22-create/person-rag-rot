from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError

from agent_mentor.application.retrieval_expansion_service import (
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
from agent_mentor.infrastructure.database.retrieval_expansion_repository import (
    SqlAlchemyRetrievalExpansionRepository,
)


class _Result:
    def __init__(self, row: object) -> None:
        self._row = row

    def one_or_none(self) -> object:
        return self._row


class _FakeSession:
    def __init__(
        self,
        *,
        row: object = None,
        scalars: list[object] | None = None,
        commit_error: Exception | None = None,
    ) -> None:
        self.row = row
        self.scalars = list(scalars or [])
        self.commit_error = commit_error
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def execute(self, _statement: object) -> _Result:
        return _Result(self.row)

    async def scalar(self, _statement: object) -> Any:
        return self.scalars.pop(0) if self.scalars else None

    def add(self, model: object) -> None:
        self.added.append(model)

    async def commit(self) -> None:
        if self.commit_error is not None:
            raise self.commit_error
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _SessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    def __call__(self) -> _FakeSession:
        return self.session


@pytest.mark.asyncio
async def test_parent_context_restores_question_policy_and_ordered_primary_ids() -> None:
    now = datetime.now(UTC)
    knowledge_base_id = UUID(int=1)
    session_id = UUID(int=2)
    parent_id = UUID(int=3)
    chunk_ids = (UUID(int=4), UUID(int=5), UUID(int=6))
    chat_session = ChatSessionModel(
        id=session_id,
        knowledge_base_id=knowledge_base_id,
        title="question",
        created_at=now,
        updated_at=now,
    )
    message = ChatMessageModel(
        id=parent_id,
        session_id=session_id,
        role="assistant",
        content="answer",
        retrieval_diagnostics={
            "allow_model_knowledge": False,
            "candidates": [{"chunk_id": str(chunk_id)} for chunk_id in chunk_ids],
        },
        created_at=now,
    )
    session = _FakeSession(row=(message, chat_session), scalars=["original question"])
    repository = SqlAlchemyRetrievalExpansionRepository(_SessionFactory(session))  # type: ignore[arg-type]

    context = await repository.parent_context(parent_id)

    assert context is not None
    assert context.knowledge_base_id == knowledge_base_id
    assert context.question == "original question"
    assert context.allow_model_knowledge is False
    assert context.primary_chunk_ids == chunk_ids


@pytest.mark.asyncio
async def test_by_parent_maps_persisted_enum_values() -> None:
    model = ChatRetrievalExpansionModel(
        id=UUID(int=10),
        parent_message_id=UUID(int=11),
        result_message_id=UUID(int=12),
        idempotency_key=UUID(int=13),
        trigger=RetrievalExpansionTrigger.USER_REQUESTED_MORE_EVIDENCE.value,
        status=RetrievalExpansionStatus.COMPLETED.value,
        request_snapshot={},
        trace={},
    )
    repository = SqlAlchemyRetrievalExpansionRepository(
        _SessionFactory(_FakeSession(scalars=[model]))  # type: ignore[arg-type]
    )

    record = await repository.by_parent(model.parent_message_id)

    assert record is not None
    assert record.expansion_id == model.id
    assert record.status is RetrievalExpansionStatus.COMPLETED
    assert record.trigger is RetrievalExpansionTrigger.USER_REQUESTED_MORE_EVIDENCE


@pytest.mark.asyncio
async def test_claim_commits_sqlalchemy_model() -> None:
    session = _FakeSession()
    repository = SqlAlchemyRetrievalExpansionRepository(_SessionFactory(session))  # type: ignore[arg-type]
    record = _record()

    result = await repository.claim(record)

    assert result is record
    assert session.committed is True
    assert len(session.added) == 1
    model = session.added[0]
    assert isinstance(model, ChatRetrievalExpansionModel)
    assert model.parent_message_id == record.parent_message_id
    assert model.request_snapshot == {}
    assert model.trace == {}


@pytest.mark.asyncio
async def test_claim_translates_unique_constraint_race_and_rolls_back() -> None:
    session = _FakeSession(commit_error=IntegrityError("insert", {}, Exception("duplicate")))
    repository = SqlAlchemyRetrievalExpansionRepository(_SessionFactory(session))  # type: ignore[arg-type]

    with pytest.raises(RetrievalExpansionClaimConflict):
        await repository.claim(_record())

    assert session.rolled_back is True


def _record() -> RetrievalExpansionRecord:
    return RetrievalExpansionRecord(
        expansion_id=UUID(int=20),
        parent_message_id=UUID(int=21),
        idempotency_key=UUID(int=22),
        trigger=RetrievalExpansionTrigger.USER_REQUESTED_MORE_EVIDENCE,
        status=RetrievalExpansionStatus.STARTED,
    )

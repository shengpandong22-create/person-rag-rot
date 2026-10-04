from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Table, UniqueConstraint

from agent_mentor.api.errors import AppError
from agent_mentor.application.retrieval_expansion_service import (
    ExpansionParentContext,
    RetrievalExpansionClaimConflict,
    RetrievalExpansionRecord,
    RetrievalExpansionRepository,
    RetrievalExpansionService,
    RetrievalExpansionStatus,
    RetrievalExpansionTrigger,
)
from agent_mentor.config import Settings
from agent_mentor.infrastructure.database.models import ChatRetrievalExpansionModel


class FakeExpansionRepository(RetrievalExpansionRepository):
    def __init__(self, parent: ExpansionParentContext | None) -> None:
        self.parent = parent
        self.existing: RetrievalExpansionRecord | None = None
        self.claimed: list[RetrievalExpansionRecord] = []
        self.conflict_winner: RetrievalExpansionRecord | None = None

    async def parent_context(self, parent_message_id: UUID) -> ExpansionParentContext | None:
        return self.parent

    async def by_parent(self, parent_message_id: UUID) -> RetrievalExpansionRecord | None:
        return self.existing

    async def claim(self, record: RetrievalExpansionRecord) -> RetrievalExpansionRecord:
        if self.conflict_winner is not None:
            self.existing = self.conflict_winner
            raise RetrievalExpansionClaimConflict
        self.claimed.append(record)
        self.existing = record
        return record


def parent_context(*, knowledge_base_id: UUID | None = None) -> ExpansionParentContext:
    return ExpansionParentContext(
        knowledge_base_id=knowledge_base_id or uuid4(),
        session_id=uuid4(),
        parent_message_id=uuid4(),
        role="assistant",
        question="为什么需要引用？",
        allow_model_knowledge=False,
        primary_chunk_ids=tuple(uuid4() for _ in range(6)),
    )


def test_retrieval_expansion_feature_flag_defaults_off() -> None:
    assert Settings().retrieval_expansion_enabled is False


def test_retrieval_expansion_model_enforces_one_shot_and_idempotency() -> None:
    table = cast(Table, ChatRetrievalExpansionModel.__table__)
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    unique_columns.update(
        tuple(column.name for column in index.columns)
        for index in table.indexes
        if index.unique
    )

    assert ("parent_message_id",) in unique_columns
    assert ("idempotency_key",) in unique_columns
    assert ("result_message_id",) in unique_columns


@pytest.mark.asyncio
async def test_disabled_service_does_not_touch_repository() -> None:
    parent = parent_context()
    repository = FakeExpansionRepository(parent)
    service = RetrievalExpansionService(repository)

    with pytest.raises(AppError) as error:
        await service.start(
            knowledge_base_id=parent.knowledge_base_id,
            parent_message_id=uuid4(),
            idempotency_key=uuid4(),
            trigger=RetrievalExpansionTrigger.USER_REQUESTED_MORE_EVIDENCE,
        )

    assert error.value.code == "RETRIEVAL_EXPANSION_DISABLED"
    assert repository.claimed == []


@pytest.mark.asyncio
async def test_enabled_service_claims_one_started_expansion() -> None:
    parent = parent_context()
    repository = FakeExpansionRepository(parent)
    service = RetrievalExpansionService(repository, enabled=True)
    key = uuid4()

    result = await service.start(
        knowledge_base_id=parent.knowledge_base_id,
        parent_message_id=parent.parent_message_id,
        idempotency_key=key,
        trigger=RetrievalExpansionTrigger.USER_REQUESTED_MORE_EVIDENCE,
    )

    assert result.status is RetrievalExpansionStatus.STARTED
    assert result.idempotency_key == key
    assert result.parent_message_id == parent.parent_message_id
    assert repository.claimed == [result]


@pytest.mark.asyncio
async def test_completed_same_key_replays_existing_record() -> None:
    parent = parent_context()
    repository = FakeExpansionRepository(parent)
    key = uuid4()
    existing = RetrievalExpansionRecord(
        expansion_id=uuid4(),
        parent_message_id=parent.parent_message_id,
        idempotency_key=key,
        trigger=RetrievalExpansionTrigger.USER_REQUESTED_MORE_EVIDENCE,
        status=RetrievalExpansionStatus.COMPLETED,
        result_message_id=uuid4(),
    )
    repository.existing = existing
    service = RetrievalExpansionService(repository, enabled=True)

    result = await service.start(
        knowledge_base_id=parent.knowledge_base_id,
        parent_message_id=parent.parent_message_id,
        idempotency_key=key,
        trigger=RetrievalExpansionTrigger.USER_REQUESTED_MORE_EVIDENCE,
    )

    assert result is existing
    assert repository.claimed == []


@pytest.mark.asyncio
async def test_different_key_cannot_repeat_parent_expansion() -> None:
    parent = parent_context()
    repository = FakeExpansionRepository(parent)
    repository.existing = RetrievalExpansionRecord(
        expansion_id=uuid4(),
        parent_message_id=parent.parent_message_id,
        idempotency_key=uuid4(),
        trigger=RetrievalExpansionTrigger.USER_REQUESTED_MORE_EVIDENCE,
        status=RetrievalExpansionStatus.COMPLETED,
    )
    service = RetrievalExpansionService(repository, enabled=True)

    with pytest.raises(AppError) as error:
        await service.start(
            knowledge_base_id=parent.knowledge_base_id,
            parent_message_id=parent.parent_message_id,
            idempotency_key=uuid4(),
            trigger=RetrievalExpansionTrigger.USER_REQUESTED_MORE_EVIDENCE,
        )

    assert error.value.code == "EXPANSION_ALREADY_EXISTS"
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_concurrent_claim_is_mapped_to_stable_conflict() -> None:
    parent = parent_context()
    repository = FakeExpansionRepository(parent)
    repository.conflict_winner = RetrievalExpansionRecord(
        expansion_id=uuid4(),
        parent_message_id=parent.parent_message_id,
        idempotency_key=uuid4(),
        trigger=RetrievalExpansionTrigger.USER_REQUESTED_MORE_EVIDENCE,
        status=RetrievalExpansionStatus.STARTED,
    )
    service = RetrievalExpansionService(repository, enabled=True)

    with pytest.raises(AppError) as error:
        await service.start(
            knowledge_base_id=parent.knowledge_base_id,
            parent_message_id=parent.parent_message_id,
            idempotency_key=uuid4(),
            trigger=RetrievalExpansionTrigger.USER_REQUESTED_MORE_EVIDENCE,
        )

    assert error.value.code == "EXPANSION_IN_PROGRESS"
    assert error.value.status_code == 409

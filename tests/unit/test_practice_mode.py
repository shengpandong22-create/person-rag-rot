from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from agent_mentor.api.errors import AppError
from agent_mentor.application import interview_service as interview_service_module
from agent_mentor.application.interview_service import InterviewService, resolve_training_plan
from agent_mentor.application.profile_service import ProfileService
from agent_mentor.domain.interview import (
    PRACTICE_DIFFICULTIES,
    PRACTICE_QUESTION_COUNTS,
    Difficulty,
    TrainingMode,
    is_practice_training_mode,
)
from agent_mentor.infrastructure.database.models import InterviewSessionModel
from agent_mentor.ports.knowledge_retriever import RetrievedChunk


class _FakeResult:
    def __init__(self, rows: list[object] | None = None) -> None:
        self._rows = list(rows or [])

    def all(self) -> list[object]:
        return list(self._rows)

    def first(self) -> object | None:
        return self._rows[0] if self._rows else None


class _ExplodingDb:
    """Database stub that fails the test on any unexpected query."""

    async def get(self, _model: object, _id: object) -> object:
        raise AssertionError("practice path must not query the database")

    async def scalar(self, _statement: object) -> object:
        raise AssertionError("practice path must not query the database")

    def scalars(self, _statement: object) -> _FakeResult:
        raise AssertionError("practice path must not query the database")

    async def execute(self, _statement: object) -> _FakeResult:
        raise AssertionError("practice path must not query the database")

    def add(self, _item: object) -> None:
        raise AssertionError("practice path must not write to the database")

    async def flush(self) -> None:
        raise AssertionError("practice path must not write to the database")


class _FakeDb:
    def __init__(
        self,
        *,
        interview: object | None = None,
        rows: list[object] | None = None,
    ) -> None:
        self.interview = interview
        self.rows = rows
        self.added: list[object] = []
        self.commits = 0

    async def get(self, _model: object, _id: object) -> object | None:
        return self.interview

    async def scalar(self, _statement: object) -> object | None:
        return None

    async def scalars(self, _statement: object) -> _FakeResult:
        return _FakeResult()

    async def execute(self, _statement: object) -> _FakeResult:
        return _FakeResult(self.rows)

    def add(self, item: object) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, _item: object) -> None:
        return None


class _FakeSessionContext:
    def __init__(self, db: _FakeDb) -> None:
        self._db = db

    async def __aenter__(self) -> _FakeDb:
        return self._db

    async def __aexit__(self, *_exc: object) -> bool:
        return False


class _FakeSessionFactory:
    def __init__(self, db: _FakeDb) -> None:
        self._db = db

    def __call__(self) -> _FakeSessionContext:
        return _FakeSessionContext(self._db)


class _FakeRetriever:
    async def retrieve(self, _query: object) -> list[RetrievedChunk]:
        return [_retrieved_chunk()]


def _retrieved_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="RAG 学习资料",
        source_url=None,
        trust_level="curated",
        heading_path=("RAG", "证据边界"),
        page_number=None,
        block_type="paragraph",
        chunk_index=1,
        content="RAG 回答必须基于检索证据，并返回可校验引用。",
        score=0.91,
        retrieval_explanation="rrf",
        vector_rank=1,
        text_rank=1,
        vector_score=0.9,
        text_score=0.8,
    )


def _practice_interview(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "id": uuid4(),
        "user_id": uuid4(),
        "knowledge_base_id": uuid4(),
        "topic": "RAG",
        "difficulty": "medium",
        "question_count": 3,
        "training_mode": "practice",
        "profile_topic_key": None,
        "profile_topic_title": None,
        "profile_subtopic_key": None,
        "profile_subtopic_title": None,
        "coverage_catalog_point_id": None,
    }
    fields.update(overrides)
    return cast(Any, SimpleNamespace(**fields))


def test_profile_training_plan_always_resolves_to_three_medium_questions() -> None:
    for difficulty, question_count in (
        (Difficulty.HARD, 1),
        (Difficulty.EASY, 10),
        (Difficulty.MEDIUM, 7),
    ):
        mode, resolved_difficulty, resolved_count = resolve_training_plan(
            training_mode=TrainingMode.PROFILE_TRAINING,
            difficulty=difficulty,
            question_count=question_count,
        )
        assert mode is TrainingMode.PROFILE_TRAINING
        assert resolved_difficulty is Difficulty.MEDIUM
        assert resolved_count == 3


def test_practice_plan_allows_controlled_counts_and_difficulties() -> None:
    for question_count in PRACTICE_QUESTION_COUNTS:
        for difficulty in PRACTICE_DIFFICULTIES:
            mode, resolved_difficulty, resolved_count = resolve_training_plan(
                training_mode=TrainingMode.PRACTICE,
                difficulty=difficulty,
                question_count=question_count,
            )
            assert mode is TrainingMode.PRACTICE
            assert resolved_difficulty is difficulty
            assert resolved_count == question_count


@pytest.mark.parametrize("question_count", [0, 2, 4, 6, 10])
def test_practice_plan_rejects_unsupported_question_counts(question_count: int) -> None:
    with pytest.raises(AppError) as error:
        resolve_training_plan(
            training_mode=TrainingMode.PRACTICE,
            difficulty=Difficulty.MEDIUM,
            question_count=question_count,
        )
    assert error.value.code == "PRACTICE_QUESTION_COUNT_INVALID"
    assert error.value.status_code == 422


def test_practice_plan_rejects_unsupported_difficulty() -> None:
    with pytest.raises(AppError) as error:
        resolve_training_plan(
            training_mode=TrainingMode.PRACTICE,
            difficulty=cast(Difficulty, "expert"),
            question_count=3,
        )
    assert error.value.code == "PRACTICE_DIFFICULTY_INVALID"
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_profile_training_create_interview_forces_contract_regardless_of_request() -> None:
    db = _FakeDb()
    service = InterviewService(
        cast(Any, _FakeSessionFactory(db)),
        cast(Any, _FakeRetriever()),
        retrieval_candidate_k=20,
    )

    session = await service.create_interview(
        knowledge_base_id=uuid4(),
        topic="LangGraph checkpoint",
        difficulty=Difficulty.HARD,
        question_count=1,
        training_mode=TrainingMode.PROFILE_TRAINING,
    )

    assert session.training_mode == "profile_training"
    assert session.difficulty == "medium"
    assert session.question_count == 3
    assert db.commits == 1


@pytest.mark.asyncio
async def test_practice_create_interview_keeps_selected_count_and_difficulty() -> None:
    db = _FakeDb()
    service = InterviewService(
        cast(Any, _FakeSessionFactory(db)),
        cast(Any, _FakeRetriever()),
        retrieval_candidate_k=20,
    )

    session = await service.create_interview(
        knowledge_base_id=uuid4(),
        topic="LangGraph checkpoint",
        difficulty=Difficulty.EASY,
        question_count=5,
        training_mode=TrainingMode.PRACTICE,
    )

    assert session.training_mode == "practice"
    assert session.difficulty == "easy"
    assert session.question_count == 5


@pytest.mark.asyncio
async def test_practice_create_interview_rejects_coverage_catalog_target() -> None:
    db = _FakeDb()
    service = InterviewService(
        cast(Any, _FakeSessionFactory(db)),
        cast(Any, _FakeRetriever()),
        retrieval_candidate_k=20,
    )

    with pytest.raises(AppError) as error:
        await service.create_interview(
            knowledge_base_id=uuid4(),
            topic="LangGraph checkpoint",
            coverage_catalog_point_id=uuid4(),
            difficulty=Difficulty.MEDIUM,
            question_count=3,
            training_mode=TrainingMode.PRACTICE,
        )

    assert error.value.code == "PRACTICE_COVERAGE_POINT_NOT_ALLOWED"
    assert db.added == []


@pytest.mark.asyncio
async def test_practice_coverage_gap_focus_is_never_selected() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = _practice_interview(coverage_catalog_point_id=uuid4())

    focus = await service._coverage_gap_focus(  # pyright: ignore[reportPrivateUsage]
        cast(Any, _ExplodingDb()),
        interview,
        sequence=1,
    )

    assert focus is None


@pytest.mark.asyncio
async def test_practice_question_does_not_record_coverage_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[dict[str, object]] = []

    async def _record_coverage(
        _db: object, *, question_id: UUID, chunk_ids: list[UUID]
    ) -> int:
        recorded.append({"question_id": question_id, "chunk_ids": chunk_ids})
        return 0

    monkeypatch.setattr(interview_service_module, "map_question_coverage", _record_coverage)
    service = object.__new__(InterviewService)
    service._llm = None  # pyright: ignore[reportPrivateUsage]
    service._retriever = cast(Any, _FakeRetriever())  # pyright: ignore[reportPrivateUsage]
    service._retrieval_candidate_k = 20  # pyright: ignore[reportPrivateUsage]
    db = _FakeDb()

    question = await service._create_question(  # pyright: ignore[reportPrivateUsage]
        cast(Any, db), _practice_interview(), sequence=1
    )

    assert question.sequence == 1
    assert recorded == []


@pytest.mark.asyncio
async def test_profile_training_question_records_coverage_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[dict[str, object]] = []

    async def _record_coverage(
        _db: object, *, question_id: UUID, chunk_ids: list[UUID]
    ) -> int:
        recorded.append({"question_id": question_id, "chunk_ids": chunk_ids})
        return len(chunk_ids)

    monkeypatch.setattr(interview_service_module, "map_question_coverage", _record_coverage)
    service = object.__new__(InterviewService)
    service._llm = None  # pyright: ignore[reportPrivateUsage]
    service._retriever = cast(Any, _FakeRetriever())  # pyright: ignore[reportPrivateUsage]
    service._retrieval_candidate_k = 20  # pyright: ignore[reportPrivateUsage]

    await service._create_question(  # pyright: ignore[reportPrivateUsage]
        cast(Any, _FakeDb()), _practice_interview(training_mode="profile_training"), sequence=1
    )

    assert len(recorded) == 1
    assert recorded[0]["chunk_ids"]


def test_practice_training_mode_detection() -> None:
    assert is_practice_training_mode(TrainingMode.PRACTICE) is True
    assert is_practice_training_mode("practice") is True
    assert is_practice_training_mode(TrainingMode.PROFILE_TRAINING) is False
    assert is_practice_training_mode("profile_training") is False


def test_interview_session_training_mode_defaults_to_profile_training() -> None:
    column = InterviewSessionModel.__table__.c.training_mode

    assert column.nullable is False
    assert column.server_default is not None
    assert str(column.server_default.arg) == "profile_training"


@pytest.mark.asyncio
async def test_practice_interview_skips_profile_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    applied: list[object] = []

    async def _record_apply(self: ProfileService, _db: object, **_fields: object) -> None:
        applied.append(_fields)

    monkeypatch.setattr(ProfileService, "_apply_evaluation", _record_apply)
    interview = _practice_interview()
    db = _FakeDb(interview=interview)
    service = ProfileService(cast(Any, _FakeSessionFactory(db)))

    snapshot = await service.apply_interview_evaluations(interview.id)

    assert applied == []
    assert snapshot.abilities == ()
    assert snapshot.review_tasks == ()


@pytest.mark.asyncio
async def test_profile_training_interview_still_applies_profile_updates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applied: list[object] = []
    evaluation_row = (
        SimpleNamespace(id=uuid4(), status="final", confidence=0.9, total=17),
        SimpleNamespace(knowledge_points=["证据边界"], question_type="concept"),
        SimpleNamespace(answer_text="RAG 需要引用白名单和证据不足降级。"),
    )

    async def _record_apply(self: ProfileService, _db: object, **_fields: object) -> None:
        applied.append(_fields)

    async def _fake_rows(
        self: ProfileService, _db: object, _interview_id: UUID
    ) -> tuple[tuple[object, object, object], ...]:
        return (evaluation_row,)

    monkeypatch.setattr(ProfileService, "_apply_evaluation", _record_apply)
    monkeypatch.setattr(ProfileService, "_evaluation_rows", _fake_rows)
    interview = _practice_interview(training_mode="profile_training")
    db = _FakeDb(interview=interview)
    service = ProfileService(cast(Any, _FakeSessionFactory(db)))

    await service.apply_interview_evaluations(interview.id)

    assert len(applied) == 1
    assert db.commits == 1

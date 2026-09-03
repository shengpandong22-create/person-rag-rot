from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy import Table, UniqueConstraint

from agent_mentor.application.interview_service import (
    QUESTION_ANGLES,
    RECENT_QUESTION_COOLDOWN_LIMIT,
    CoverageFocus,
    InterviewQuestionOutput,
    InterviewService,
)
from agent_mentor.domain.interview import Difficulty, QuestionType
from agent_mentor.infrastructure.database.models import QuestionCoverageModel, UserAnswerModel


class _FakeSession:
    def __init__(self, existing: object | None = None) -> None:
        self.existing = existing
        self.added: list[object] = []

    async def scalar(self, _statement: object) -> object | None:
        return self.existing

    def add(self, item: object) -> None:
        self.added.append(item)


def test_coverage_gap_sequence_reserves_second_question_for_multi_question_interview() -> None:
    service = InterviewService.__new__(InterviewService)

    assert service._coverage_gap_sequence(3) == 2
    assert service._coverage_gap_sequence(2) == 2
    assert service._coverage_gap_sequence(1) == 1


def test_question_search_text_includes_coverage_focus_when_present() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = SimpleNamespace(
        id=uuid4(),
        knowledge_base_id=uuid4(),
        topic="RAG",
        difficulty=Difficulty.MEDIUM,
    )
    angle = QUESTION_ANGLES[2]

    query = service._question_search_text(
        cast(Any, interview),
        QuestionType.SCENARIO,
        "引用白名单与证据边界",
        angle,
    )

    assert "RAG" in query
    assert "工程落地" in query
    assert angle.title in query
    assert angle.search_hint in query
    assert "覆盖盲区" in query
    assert "引用白名单与证据边界" in query


def test_coverage_focus_carries_point_id_and_title() -> None:
    point_id = uuid4()
    focus = CoverageFocus(point_id=point_id, title="引用白名单与证据边界")

    assert focus.point_id == point_id
    assert focus.title == "引用白名单与证据边界"


def test_coverage_gap_focus_prioritizes_points_with_more_sources() -> None:
    service = InterviewService.__new__(InterviewService)

    statement = service._coverage_gap_focus_statement(uuid4())
    compiled = str(statement.compile(compile_kwargs={"literal_binds": False})).lower()

    assert "count(" in compiled
    assert "order by count(knowledge_catalog_sources.id) desc" in compiled


def test_recent_question_statement_scopes_to_same_knowledge_base_and_excludes_current() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = SimpleNamespace(id=uuid4(), knowledge_base_id=uuid4())

    statement = service._recent_question_statement(cast(Any, interview))
    compiled_statement = statement.compile(compile_kwargs={"literal_binds": False})
    compiled = str(compiled_statement).lower()

    assert "interview_sessions.knowledge_base_id" in compiled
    assert "interview_sessions.id !=" in compiled or "interview_sessions.id ! =" in compiled
    assert RECENT_QUESTION_COOLDOWN_LIMIT in compiled_statement.params.values()


def test_question_search_text_keeps_original_query_without_coverage_focus() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = SimpleNamespace(
        id=uuid4(),
        knowledge_base_id=uuid4(),
        topic="LangGraph",
        difficulty=Difficulty.HARD,
    )

    query = service._question_search_text(cast(Any, interview), QuestionType.CONCEPT, None)

    assert "LangGraph" in query
    assert "定义 原理 核心概念" in query
    assert "覆盖盲区" not in query


def test_question_angle_rotates_by_interview_and_sequence() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = SimpleNamespace(
        id=uuid4(),
        knowledge_base_id=uuid4(),
        topic="RAG",
        difficulty=Difficulty.MEDIUM,
    )

    first = service._question_angle(cast(Any, interview), 1)
    second = service._question_angle(cast(Any, interview), 2)
    third = service._question_angle(cast(Any, interview), 3)

    assert len({first.key, second.key, third.key}) == 3
    assert first in QUESTION_ANGLES
    assert second in QUESTION_ANGLES
    assert third in QUESTION_ANGLES


def test_deterministic_question_text_exposes_angle() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = SimpleNamespace(
        id=uuid4(),
        topic="RAG",
        question_count=3,
    )
    angle = QUESTION_ANGLES[0]

    question = service._question_text(cast(Any, interview), 1, angle, [])

    assert angle.title in question
    assert "易混淆点" in question


def test_question_output_defaults_to_llm_generation_mode() -> None:
    output = InterviewQuestionOutput(
        question_text="请说明 RAG 的核心边界。",
        reference_answer="RAG 需要基于检索证据回答。",
        required_points=["证据边界"],
    )

    assert output.generation_mode == "llm"
    assert output.fallback_reason is None


def test_question_prompt_includes_recent_history_cooldown() -> None:
    service = object.__new__(InterviewService)
    interview = SimpleNamespace(
        topic="RAG",
        difficulty="medium",
        question_count=3,
    )

    prompt = service._question_prompt(  # pyright: ignore[reportPrivateUsage, reportArgumentType]
        cast(Any, interview),
        1,
        QuestionType.CONCEPT,
        QUESTION_ANGLES[0],
        [],
        ["本轮题目"],
        ["历史题目 A", "历史题目 B"],
        None,
    )

    assert "同知识库最近历史题目" in prompt
    assert "历史题目 A" in prompt
    assert "避开最近历史题目的核心问法" in prompt


def test_user_answer_idempotency_is_enforced_by_database_constraint() -> None:
    table = cast(Table, UserAnswerModel.__table__)
    constraints = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert any(
        constraint.name == "uq_answer_idempotency"
        and {column.name for column in constraint.columns}
        == {"question_id", "idempotency_key"}
        for constraint in constraints
    )


@pytest.mark.asyncio
async def test_ensure_question_coverage_adds_missing_focus_point() -> None:
    service = InterviewService.__new__(InterviewService)
    db = _FakeSession()
    question_id = uuid4()
    knowledge_point_id = uuid4()

    await service._ensure_question_coverage(
        cast(Any, db),
        question_id=question_id,
        knowledge_point_id=knowledge_point_id,
    )

    assert len(db.added) == 1
    coverage = db.added[0]
    assert isinstance(coverage, QuestionCoverageModel)
    assert coverage.question_id == question_id
    assert coverage.knowledge_point_id == knowledge_point_id


@pytest.mark.asyncio
async def test_ensure_question_coverage_keeps_existing_focus_point() -> None:
    service = InterviewService.__new__(InterviewService)
    db = _FakeSession(existing=uuid4())

    await service._ensure_question_coverage(
        cast(Any, db),
        question_id=uuid4(),
        knowledge_point_id=uuid4(),
    )

    assert db.added == []

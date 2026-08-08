from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

from agent_mentor.application.interview_service import InterviewService
from agent_mentor.domain.interview import Difficulty, QuestionType


def test_coverage_gap_sequence_reserves_second_question_for_multi_question_interview() -> None:
    service = InterviewService.__new__(InterviewService)

    assert service._coverage_gap_sequence(3) == 2
    assert service._coverage_gap_sequence(2) == 2
    assert service._coverage_gap_sequence(1) == 1


def test_question_search_text_includes_coverage_focus_when_present() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = SimpleNamespace(
        knowledge_base_id=uuid4(),
        topic="RAG",
        difficulty=Difficulty.MEDIUM,
    )

    query = service._question_search_text(
        cast(Any, interview),
        QuestionType.SCENARIO,
        "引用白名单与证据边界",
    )

    assert "RAG" in query
    assert "工程落地" in query
    assert "覆盖盲区" in query
    assert "引用白名单与证据边界" in query


def test_question_search_text_keeps_original_query_without_coverage_focus() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = SimpleNamespace(
        knowledge_base_id=uuid4(),
        topic="LangGraph",
        difficulty=Difficulty.HARD,
    )

    query = service._question_search_text(cast(Any, interview), QuestionType.CONCEPT, None)

    assert "LangGraph" in query
    assert "定义 原理 核心概念" in query
    assert "覆盖盲区" not in query

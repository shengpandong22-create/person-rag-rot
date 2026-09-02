from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from agent_mentor.application.interview_service import QUESTION_ANGLES, InterviewService
from agent_mentor.domain.interview import InterviewStatus, assert_transition, can_transition
from agent_mentor.workflows.interview import (
    InterviewWorkflowState,
    advance_question,
    checkpoint_summary,
    finish_interview,
    wait_for_answer,
    workflow_node_spec,
)


def state() -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=uuid4(),
        thread_id="thread-1",
        current_node="created",
        current_question_index=0,
        question_count=3,
        waiting_for_answer=False,
    )


def test_interview_status_machine_rejects_illegal_transition() -> None:
    assert can_transition(InterviewStatus.CREATED, InterviewStatus.WAITING_FOR_ANSWER)
    assert not can_transition(InterviewStatus.COMPLETED, InterviewStatus.WAITING_FOR_ANSWER)

    with pytest.raises(ValueError):
        assert_transition(InterviewStatus.COMPLETED, InterviewStatus.WAITING_FOR_ANSWER)


def test_workflow_checkpoint_is_bounded() -> None:
    waiting = wait_for_answer(state())

    checkpoint = waiting.checkpoint()

    assert checkpoint == {
        "session_id": str(waiting.session_id),
        "thread_id": "thread-1",
        "current_node": "wait_for_answer",
        "current_question_index": 0,
        "question_count": 3,
        "waiting_for_answer": True,
    }
    assert "content" not in checkpoint
    assert "documents" not in checkpoint


def test_workflow_advances_and_finishes_deterministically() -> None:
    next_state = advance_question(state())
    finished = finish_interview(next_state)

    assert next_state.current_question_index == 1
    assert next_state.current_node == "advance_question"
    assert finished.current_node == "finish_interview"
    assert not finished.waiting_for_answer


def test_workflow_node_specs_expose_interview_agent_events() -> None:
    generated = workflow_node_spec("generate_question")
    waiting = wait_for_answer(state())
    input_summary, output_summary = checkpoint_summary(waiting.checkpoint())

    assert generated.event == "question.generated"
    assert generated.label == "生成题目"
    assert input_summary == "question_index=0/3"
    assert output_summary == "等待用户回答，可刷新后恢复"


def test_interview_questions_use_progressive_templates() -> None:
    service = object.__new__(InterviewService)
    interview = SimpleNamespace(id=uuid4(), topic="RAG", question_count=3)

    questions = [
        service._question_text(  # pyright: ignore[reportPrivateUsage, reportArgumentType]
            cast(Any, interview),
            sequence,
            QUESTION_ANGLES[sequence - 1],
            chunks=[],
        )
        for sequence in range(1, 4)
    ]

    assert len(set(questions)) == 3
    assert questions[0].startswith("[1/3] 请从")
    assert "落地到自己的 AI 面试助手项目" in questions[1]
    assert "从面试官视角复盘" in questions[2]


def test_interview_question_similarity_guard_rejects_repeated_core_question() -> None:
    service = object.__new__(InterviewService)

    assert service._is_too_similar(  # pyright: ignore[reportPrivateUsage]
        "请说明 RAG 检索增强生成的核心概念和主要流程。",
        ["请说明 RAG 检索增强生成的核心概念以及主要流程。"],
    )
    assert not service._is_too_similar(  # pyright: ignore[reportPrivateUsage]
        "请设计 RAG 服务超时时的降级、监控和故障恢复方案。",
        ["请说明 RAG 检索增强生成的核心概念以及主要流程。"],
    )

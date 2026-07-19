from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class InterviewWorkflowState:
    session_id: UUID
    thread_id: str
    current_node: str
    current_question_index: int
    question_count: int
    waiting_for_answer: bool

    def checkpoint(self) -> dict[str, object]:
        return {
            "session_id": str(self.session_id),
            "thread_id": self.thread_id,
            "current_node": self.current_node,
            "current_question_index": self.current_question_index,
            "question_count": self.question_count,
            "waiting_for_answer": self.waiting_for_answer,
        }


def load_profile(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="load_profile",
        current_question_index=state.current_question_index,
        question_count=state.question_count,
        waiting_for_answer=False,
    )


def plan_interview(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="plan_interview",
        current_question_index=state.current_question_index,
        question_count=state.question_count,
        waiting_for_answer=False,
    )


def generate_question(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="generate_question",
        current_question_index=state.current_question_index,
        question_count=state.question_count,
        waiting_for_answer=False,
    )


def wait_for_answer(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="wait_for_answer",
        current_question_index=state.current_question_index,
        question_count=state.question_count,
        waiting_for_answer=True,
    )


def persist_answer(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="persist_answer",
        current_question_index=state.current_question_index,
        question_count=state.question_count,
        waiting_for_answer=False,
    )


def advance_question(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="advance_question",
        current_question_index=state.current_question_index + 1,
        question_count=state.question_count,
        waiting_for_answer=False,
    )


def finish_interview(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="finish_interview",
        current_question_index=state.current_question_index,
        question_count=state.question_count,
        waiting_for_answer=False,
    )

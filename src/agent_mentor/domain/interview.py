from __future__ import annotations

from enum import StrEnum


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class InterviewStatus(StrEnum):
    CREATED = "created"
    WAITING_FOR_ANSWER = "waiting_for_answer"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class QuestionType(StrEnum):
    CONCEPT = "concept"
    SCENARIO = "scenario"
    DESIGN = "design"
    DEBUGGING = "debugging"


class AnswerKind(StrEnum):
    PRIMARY = "primary"
    FOLLOW_UP = "follow_up"


class FollowUpStatus(StrEnum):
    PENDING = "pending"
    ANSWERED = "answered"
    SKIPPED = "skipped"


ALLOWED_STATUS_TRANSITIONS = {
    InterviewStatus.CREATED: {InterviewStatus.WAITING_FOR_ANSWER, InterviewStatus.CANCELLED},
    InterviewStatus.WAITING_FOR_ANSWER: {
        InterviewStatus.WAITING_FOR_ANSWER,
        InterviewStatus.COMPLETED,
        InterviewStatus.CANCELLED,
    },
    InterviewStatus.COMPLETED: set(),
    InterviewStatus.CANCELLED: set(),
}


def can_transition(from_status: InterviewStatus, to_status: InterviewStatus) -> bool:
    return to_status in ALLOWED_STATUS_TRANSITIONS[from_status]


def assert_transition(from_status: str, to_status: InterviewStatus) -> None:
    current = InterviewStatus(from_status)
    if not can_transition(current, to_status):
        raise ValueError(f"Illegal interview status transition: {current} -> {to_status}")

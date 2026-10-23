from __future__ import annotations

from enum import StrEnum


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TrainingMode(StrEnum):
    """Whether an interview feeds the official ability profile.

    ``PROFILE_TRAINING`` is the default, fully accounted training path.
    ``PRACTICE`` is a controlled drill that may generate questions, answers
    and reports but must never mutate profile or coverage accounting.
    """

    PROFILE_TRAINING = "profile_training"
    PRACTICE = "practice"


PROFILE_TRAINING_QUESTION_COUNT = 3
PROFILE_TRAINING_DIFFICULTY = Difficulty.MEDIUM
PRACTICE_QUESTION_COUNTS: tuple[int, ...] = (1, 3, 5)
PRACTICE_DIFFICULTIES: tuple[Difficulty, ...] = (
    Difficulty.EASY,
    Difficulty.MEDIUM,
    Difficulty.HARD,
)


def is_practice_training_mode(training_mode: str | TrainingMode) -> bool:
    """Tell whether a persisted or in-memory training mode is practice."""
    return str(training_mode) == TrainingMode.PRACTICE.value


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

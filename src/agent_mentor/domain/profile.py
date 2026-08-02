from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, Field

from agent_mentor.domain.evaluation import EvaluationStatus


class ErrorType(StrEnum):
    CONCEPT_CONFUSION = "concept_confusion"
    MISSING_DETAIL = "missing_detail"
    INCORRECT_REASONING = "incorrect_reasoning"
    SCENARIO_MISAPPLICATION = "scenario_misapplication"
    UNCLEAR_COMMUNICATION = "unclear_communication"
    NO_ANSWER = "no_answer"


class ReviewTaskStatus(StrEnum):
    OPEN = "open"
    COMPLETED = "completed"


class ProfileUpdateDecision(BaseModel):
    should_update: bool
    reason: str
    confidence_weight: float = Field(ge=0, le=1)


class TrainingFocusCandidate(BaseModel):
    knowledge_point: str
    topic_key: str | None = None
    topic_title: str | None = None
    subtopic_key: str | None = None
    subtopic_title: str | None = None
    reason: str
    priority: int = Field(ge=1, le=5)
    mastery_score: float | None = Field(default=None, ge=0, le=1)
    source_type: str


def profile_update_decision(status: str, confidence: float) -> ProfileUpdateDecision:
    if status in {EvaluationStatus.DISPUTED, EvaluationStatus.REVIEW_PENDING}:
        return ProfileUpdateDecision(
            should_update=False,
            reason=f"skip_{status}",
            confidence_weight=0,
        )
    if confidence < 0.70:
        return ProfileUpdateDecision(
            should_update=True,
            reason="low_confidence_final",
            confidence_weight=0.5,
        )
    return ProfileUpdateDecision(
        should_update=True,
        reason="trusted_final",
        confidence_weight=1.0,
    )


def normalized_score(total: int, max_score: int = 20) -> float:
    if max_score <= 0:
        raise ValueError("max_score must be positive.")
    return max(0.0, min(1.0, total / max_score))


def updated_mastery(
    current_mastery: float,
    score: float,
    *,
    confidence_weight: float,
    difficulty: str,
) -> float:
    difficulty_factor = {"easy": 0.85, "medium": 1.0, "hard": 1.15}.get(difficulty, 1.0)
    learning_rate = min(0.35, 0.18 * confidence_weight * difficulty_factor)
    return round(current_mastery + (score - current_mastery) * learning_rate, 4)


def classify_error(total: int, dimensions: dict[str, int], answer_text: str) -> ErrorType | None:
    if not answer_text.strip():
        return ErrorType.NO_ANSWER
    if total >= 16:
        return None
    weakest = min(dimensions.items(), key=lambda item: item[1])[0]
    if weakest == "correctness":
        return ErrorType.CONCEPT_CONFUSION
    if weakest == "completeness":
        return ErrorType.MISSING_DETAIL
    if weakest == "reasoning":
        return ErrorType.INCORRECT_REASONING
    if weakest == "communication":
        return ErrorType.UNCLEAR_COMMUNICATION
    return ErrorType.SCENARIO_MISAPPLICATION


def next_review_due(now: datetime, occurrence_count: int) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    if occurrence_count <= 1:
        return now + timedelta(days=1)
    if occurrence_count == 2:
        return now + timedelta(days=3)
    return now + timedelta(days=7)


def task_priority(occurrence_count: int, mastery_score: float) -> int:
    severity = 3 if mastery_score < 0.45 else 2 if mastery_score < 0.7 else 1
    repetition = 2 if occurrence_count >= 3 else 1 if occurrence_count == 2 else 0
    return min(5, severity + repetition)


def review_verification_progress(
    current_streak: int,
    priority: int,
    *,
    trusted_high_score: bool,
) -> tuple[int, int, bool]:
    if not trusted_high_score:
        return 0, priority, False
    next_streak = min(2, current_streak + 1)
    return next_streak, max(1, priority - 1), next_streak >= 2


def rank_training_focuses(
    candidates: list[TrainingFocusCandidate], *, limit: int = 5
) -> list[TrainingFocusCandidate]:
    """Rank profile-derived topics for the next interview round.

    Review tasks are stronger signals than passive low-mastery abilities because they represent
    concrete mistakes observed in recent interviews. Lower mastery should also move a topic up.
    """
    best_by_point: dict[str, TrainingFocusCandidate] = {}
    for candidate in candidates:
        point = candidate.knowledge_point.strip()
        if not point:
            continue
        routing_key = f"{candidate.topic_key or ''}:{candidate.subtopic_key or ''}:{point}"
        existing = best_by_point.get(routing_key)
        if existing is None or _focus_sort_key(candidate) < _focus_sort_key(existing):
            best_by_point[routing_key] = candidate
    ranked = sorted(best_by_point.values(), key=_focus_sort_key)
    return ranked[:limit]


def _focus_sort_key(candidate: TrainingFocusCandidate) -> tuple[int, int, float, str]:
    source_rank = 0 if candidate.source_type == "review_task" else 1
    mastery = candidate.mastery_score if candidate.mastery_score is not None else 1.0
    return (source_rank, -candidate.priority, mastery, candidate.knowledge_point)

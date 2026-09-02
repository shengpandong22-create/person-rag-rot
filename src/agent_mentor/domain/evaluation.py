from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class EvaluationStatus(StrEnum):
    FINAL = "final"
    REVIEW_PENDING = "review_pending"
    DISPUTED = "disputed"


class ReviewDecision(StrEnum):
    NOT_REQUIRED = "not_required"
    USED_REVIEW = "used_review"
    PENDING = "pending"
    DISPUTED = "disputed"


class RubricItem(BaseModel):
    criterion: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=800)
    weight: int = Field(ge=1, le=100)
    required_points: list[str] = Field(default_factory=list)


class EvaluationRubric(BaseModel):
    items: list[RubricItem] = Field(min_length=1)
    max_score: int = 20

    @model_validator(mode="after")
    def weights_total_one_hundred(self) -> EvaluationRubric:
        if sum(item.weight for item in self.items) != 100:
            raise ValueError("Rubric weights must total 100.")
        return self


class EvaluationOutput(BaseModel):
    correctness: int = Field(ge=0, le=5)
    completeness: int = Field(ge=0, le=5)
    reasoning: int = Field(ge=0, le=5)
    communication: int = Field(ge=0, le=5)
    confidence: float = Field(ge=0, le=1)
    covered_points: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    incorrect_claims: list[str] = Field(default_factory=list)
    answer_evidence: list[str] = Field(default_factory=list)
    reference_chunk_ids: list[UUID] = Field(default_factory=list)
    feedback: str = Field(min_length=1)
    follow_up_recommended: bool = False
    review_reasons: list[str] = Field(default_factory=list)


HARD_MODEL_REVIEW_REASONS = {
    "boundary_with_dispute",
    "citation_invalid",
    "dimension_conflict",
    "factual_conflict",
    "hallucination",
    "illegal_citation",
    "low_confidence",
    "severe_quality_gap",
}


def total_score(output: EvaluationOutput) -> int:
    return output.correctness + output.completeness + output.reasoning + output.communication


def review_reasons_for(output: EvaluationOutput) -> list[str]:
    reasons = [
        reason for reason in output.review_reasons if reason in HARD_MODEL_REVIEW_REASONS
    ]
    if output.confidence < 0.70:
        reasons.append("low_confidence")
    total = total_score(output)
    if total <= 8 and (output.correctness <= 2 or len(output.missing_points) >= 2):
        reasons.append("severe_quality_gap")
    if total in {9, 10, 11, 12} and output.incorrect_claims:
        reasons.append("boundary_with_dispute")
    if (
        max(output.correctness, output.completeness, output.reasoning, output.communication)
        - min(output.correctness, output.completeness, output.reasoning, output.communication)
        >= 4
    ):
        reasons.append("dimension_conflict")
    return sorted(set(reasons))


def should_review(output: EvaluationOutput) -> bool:
    return bool(review_reasons_for(output))


def initial_review_route(
    output: EvaluationOutput, *, reviewer_available: bool
) -> tuple[EvaluationStatus, ReviewDecision]:
    if not should_review(output):
        return EvaluationStatus.FINAL, ReviewDecision.NOT_REQUIRED
    if not reviewer_available:
        return EvaluationStatus.REVIEW_PENDING, ReviewDecision.PENDING
    return EvaluationStatus.FINAL, ReviewDecision.USED_REVIEW

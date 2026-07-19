from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agent_mentor.api.errors import AppError
from agent_mentor.application.evaluation_service import EvaluationService
from agent_mentor.domain.evaluation import (
    EvaluationOutput,
    EvaluationRubric,
    EvaluationStatus,
    ReviewDecision,
    RubricItem,
    initial_review_route,
    should_review,
    total_score,
)
from agent_mentor.infrastructure.database.models import InterviewQuestionModel, UserAnswerModel


def valid_rubric() -> EvaluationRubric:
    return EvaluationRubric(
        items=[
            RubricItem(
                criterion="correctness",
                description="概念准确",
                weight=25,
                required_points=["RAG", "引用"],
            ),
            RubricItem(criterion="completeness", description="覆盖完整", weight=25),
            RubricItem(criterion="reasoning", description="推理清晰", weight=25),
            RubricItem(criterion="communication", description="表达清楚", weight=25),
        ]
    )


def question() -> InterviewQuestionModel:
    return InterviewQuestionModel(
        id=uuid4(),
        session_id=uuid4(),
        sequence=1,
        question_text="解释 RAG 为什么需要引用。",
        question_type="concept",
        difficulty="medium",
        knowledge_points=["RAG"],
        reference_answer="RAG uses retrieved evidence and citations to reduce hallucination.",
        rubric=valid_rubric().model_dump(),
        prompt_version="interview_question_v1",
    )


def answer(text: str) -> UserAnswerModel:
    return UserAnswerModel(
        id=uuid4(),
        question_id=uuid4(),
        answer_text=text,
        answer_kind="primary",
        idempotency_key="test-key",
    )


def test_rubric_rejects_weight_sum_not_one_hundred() -> None:
    with pytest.raises(ValidationError):
        EvaluationRubric(
            items=[
                RubricItem(criterion="a", description="a", weight=60),
                RubricItem(criterion="b", description="b", weight=30),
            ]
        )


def test_evaluation_score_bounds_are_validated() -> None:
    with pytest.raises(ValidationError):
        EvaluationOutput(
            correctness=6,
            completeness=1,
            reasoning=1,
            communication=1,
            confidence=0.8,
            feedback="invalid",
        )


def test_total_score_is_computed_by_application() -> None:
    output = EvaluationOutput(
        correctness=4,
        completeness=3,
        reasoning=2,
        communication=1,
        confidence=0.8,
        feedback="ok",
    )

    assert total_score(output) == 10


def test_low_confidence_result_enters_review_route() -> None:
    output = EvaluationOutput(
        correctness=2,
        completeness=2,
        reasoning=2,
        communication=2,
        confidence=0.55,
        feedback="needs review",
    )

    assert should_review(output)


def test_reviewer_unavailable_marks_pending() -> None:
    output = EvaluationOutput(
        correctness=2,
        completeness=2,
        reasoning=2,
        communication=2,
        confidence=0.55,
        feedback="needs review",
    )

    status, decision = initial_review_route(output, reviewer_available=False)

    assert should_review(output)
    assert status == EvaluationStatus.REVIEW_PENDING
    assert decision == ReviewDecision.PENDING


def test_illegal_evaluation_citation_is_rejected() -> None:
    service = EvaluationService(cast(Any, None))

    with pytest.raises(AppError) as error:
        service._assert_allowed_references([uuid4()], (uuid4(),))

    assert error.value.code == "EVALUATION_CITATION_INVALID"


def test_deterministic_evaluator_uses_only_question_references() -> None:
    service = EvaluationService(cast(Any, None))
    allowed = (uuid4(), uuid4())

    first = service._evaluate_deterministically(
        question(),
        answer("RAG 会先检索 evidence，再通过引用 citation 降低幻觉，因为答案可回溯。"),
        allowed,
    )
    second = service._evaluate_deterministically(
        question(),
        answer("RAG 会先检索 evidence，再通过引用 citation 降低幻觉，因为答案可回溯。"),
        allowed,
    )

    assert first == second
    assert set(first.reference_chunk_ids).issubset(set(allowed))

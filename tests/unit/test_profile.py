from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agent_mentor.domain.evaluation import EvaluationStatus
from agent_mentor.domain.profile import (
    ErrorType,
    TrainingFocusCandidate,
    classify_error,
    next_review_due,
    normalized_score,
    profile_update_decision,
    rank_training_focuses,
    review_verification_progress,
    task_priority,
    updated_mastery,
)


def test_review_task_requires_two_consecutive_trusted_high_scores() -> None:
    streak, priority, completed = review_verification_progress(0, 4, trusted_high_score=True)
    assert (streak, priority, completed) == (1, 3, False)

    streak, priority, completed = review_verification_progress(
        streak, priority, trusted_high_score=False
    )
    assert (streak, priority, completed) == (0, 3, False)

    streak, priority, completed = review_verification_progress(
        streak, priority, trusted_high_score=True
    )
    streak, priority, completed = review_verification_progress(
        streak, priority, trusted_high_score=True
    )
    assert (streak, priority, completed) == (2, 1, True)


def test_disputed_and_pending_evaluations_do_not_update_profile() -> None:
    disputed = profile_update_decision(EvaluationStatus.DISPUTED, 0.9)
    pending = profile_update_decision(EvaluationStatus.REVIEW_PENDING, 0.9)

    assert not disputed.should_update
    assert not pending.should_update
    assert disputed.confidence_weight == 0
    assert pending.confidence_weight == 0


def test_low_confidence_final_evaluation_updates_with_reduced_weight() -> None:
    decision = profile_update_decision(EvaluationStatus.FINAL, 0.55)

    assert decision.should_update
    assert decision.confidence_weight == 0.5


def test_mastery_update_is_bounded_and_confidence_weighted() -> None:
    full_weight = updated_mastery(
        0.5, normalized_score(16), confidence_weight=1, difficulty="medium"
    )
    low_weight = updated_mastery(
        0.5, normalized_score(16), confidence_weight=0.5, difficulty="medium"
    )

    assert 0.5 < low_weight < full_weight < 1


def test_error_type_uses_weakest_dimension() -> None:
    assert (
        classify_error(
            10,
            {"correctness": 4, "completeness": 2, "reasoning": 3, "communication": 3},
            "回答不完整",
        )
        == ErrorType.MISSING_DETAIL
    )
    assert classify_error(17, {"correctness": 4}, "高分答案") is None
    assert classify_error(0, {"correctness": 0}, "   ") == ErrorType.NO_ANSWER


def test_review_task_due_interval_follows_occurrence_count() -> None:
    now = datetime(2026, 7, 19, tzinfo=UTC)

    assert next_review_due(now, 1) == now + timedelta(days=1)
    assert next_review_due(now, 2) == now + timedelta(days=3)
    assert next_review_due(now, 3) == now + timedelta(days=7)


def test_review_task_priority_combines_repetition_and_mastery() -> None:
    assert task_priority(1, 0.8) == 1
    assert task_priority(2, 0.6) == 3
    assert task_priority(3, 0.3) == 5


def test_training_focuses_prefer_review_tasks_and_lower_mastery() -> None:
    ranked = rank_training_focuses(
        [
            TrainingFocusCandidate(
                knowledge_point="RAG 检索增强生成",
                reason="low_mastery",
                priority=2,
                mastery_score=0.4,
                source_type="ability",
            ),
            TrainingFocusCandidate(
                knowledge_point="状态建模与工作流控制",
                reason="due_review_task:concept_confusion",
                priority=3,
                mastery_score=0.55,
                source_type="review_task",
            ),
            TrainingFocusCandidate(
                knowledge_point="RAG 检索增强生成",
                reason="due_review_task:missing_detail",
                priority=4,
                mastery_score=0.4,
                source_type="review_task",
            ),
        ]
    )

    assert [item.knowledge_point for item in ranked] == [
        "RAG 检索增强生成",
        "状态建模与工作流控制",
    ]
    assert ranked[0].source_type == "review_task"


def test_training_focuses_do_not_merge_same_title_from_different_parents() -> None:
    ranked = rank_training_focuses(
        [
            TrainingFocusCandidate(
                knowledge_point="评估与可靠性",
                topic_key="rag",
                subtopic_key="evaluation",
                reason="due_review_task:concept_confusion",
                priority=3,
                mastery_score=0.44,
                source_type="review_task",
            ),
            TrainingFocusCandidate(
                knowledge_point="评估与可靠性",
                topic_key="agent_engineering",
                subtopic_key="evaluation",
                reason="low_mastery",
                priority=2,
                mastery_score=0.60,
                source_type="ability",
            ),
        ]
    )

    assert [(item.topic_key, item.subtopic_key) for item in ranked] == [
        ("rag", "evaluation"),
        ("agent_engineering", "evaluation"),
    ]

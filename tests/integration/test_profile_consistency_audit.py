from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from agent_mentor.application.knowledge_service import DEFAULT_USER_ID
from agent_mentor.application.profile_service import ProfileService
from agent_mentor.domain.evaluation import EvaluationStatus, ReviewDecision
from agent_mentor.domain.interview import AnswerKind, Difficulty, InterviewStatus
from agent_mentor.domain.profile import ReviewTaskStatus
from agent_mentor.infrastructure.database.models import (
    EvaluationModel,
    InterviewQuestionModel,
    InterviewSessionModel,
    KnowledgeBaseModel,
    ProfileUpdateEventModel,
    UserAnswerModel,
)
from agent_mentor.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)

DATABASE_URL = os.getenv("AGENT_MENTOR_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="isolated PostgreSQL test DB not configured",
)


async def _seed_evaluation(
    sessions,
    *,
    knowledge_base_id: UUID,
    sequence: int,
    subtopic_key: str,
    subtopic_title: str,
    total: int,
    confidence: float,
    status: EvaluationStatus,
) -> UUID:
    now = datetime.now(UTC)
    interview_id = uuid4()
    question_id = uuid4()
    answer_id = uuid4()
    evaluation_id = uuid4()
    async with sessions() as db:
        db.add(
            InterviewSessionModel(
                id=interview_id,
                user_id=DEFAULT_USER_ID,
                knowledge_base_id=knowledge_base_id,
                topic="LangGraph checkpoint",
                profile_topic_key="langgraph",
                profile_topic_title="LangGraph",
                profile_subtopic_key=subtopic_key,
                profile_subtopic_title=subtopic_title,
                difficulty=Difficulty.MEDIUM,
                question_count=1,
                status=InterviewStatus.COMPLETED,
                current_question_index=1,
                workflow_thread_id=str(interview_id),
                started_at=now,
                completed_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            InterviewQuestionModel(
                id=question_id,
                session_id=interview_id,
                sequence=sequence,
                question_text="Checkpoint 如何支持恢复？",
                question_type="concept",
                difficulty=Difficulty.MEDIUM,
                knowledge_points=["checkpoint"],
                reference_answer="保存状态并在中断后恢复。",
                rubric={"items": []},
                prompt_version="profile-audit-v1",
                placeholder_feedback=None,
                created_at=now,
            )
        )
        db.add(
            UserAnswerModel(
                id=answer_id,
                question_id=question_id,
                answer_text="有明确的工程解释。",
                answer_kind=AnswerKind.PRIMARY,
                idempotency_key=str(answer_id),
                submitted_at=now,
            )
        )
        db.add(
            EvaluationModel(
                id=evaluation_id,
                question_id=question_id,
                answer_id=answer_id,
                correctness=min(5, total // 4),
                completeness=min(5, total // 4),
                reasoning=min(5, total // 4),
                communication=min(5, total // 4),
                total=total,
                confidence=confidence,
                covered_points=["checkpoint"],
                missing_points=[],
                incorrect_claims=[],
                answer_evidence=[],
                feedback="audit fixture",
                follow_up_recommended=False,
                needs_review=status == EvaluationStatus.REVIEW_PENDING,
                reviewed=status != EvaluationStatus.REVIEW_PENDING,
                review_reasons=[],
                review_decision=(
                    ReviewDecision.PENDING
                    if status == EvaluationStatus.REVIEW_PENDING
                    else ReviewDecision.DISPUTED
                    if status == EvaluationStatus.DISPUTED
                    else ReviewDecision.NOT_REQUIRED
                ),
                status=status,
                model_name="audit-fixture",
                prompt_version="profile-audit-v1",
                created_at=now,
            )
        )
        await db.commit()
    return interview_id


@pytest.mark.asyncio
async def test_profile_update_rules_and_review_completion_boundary() -> None:
    assert DATABASE_URL is not None
    engine = create_database_engine(DATABASE_URL)
    sessions = create_session_factory(engine)
    profiles = ProfileService(sessions)
    now = datetime.now(UTC)

    try:
        async with sessions() as db:
            base = KnowledgeBaseModel(
                id=uuid4(),
                user_id=DEFAULT_USER_ID,
                name=f"profile-audit-{uuid4()}",
                description="isolated profile consistency audit",
                created_at=now,
                updated_at=now,
            )
            isolated_base = KnowledgeBaseModel(
                id=uuid4(),
                user_id=DEFAULT_USER_ID,
                name=f"profile-audit-isolated-{uuid4()}",
                description="isolation control",
                created_at=now,
                updated_at=now,
            )
            db.add_all((base, isolated_base))
            await db.commit()

        low_interview = await _seed_evaluation(
            sessions,
            knowledge_base_id=base.id,
            sequence=1,
            subtopic_key="checkpoint",
            subtopic_title="Checkpoint 与恢复",
            total=4,
            confidence=0.95,
            status=EvaluationStatus.FINAL,
        )
        first = await profiles.apply_interview_evaluations(low_interview)
        checkpoint_task = next(
            task for task in first.review_tasks if task.subtopic_key == "checkpoint"
        )
        assert checkpoint_task.status == ReviewTaskStatus.OPEN
        assert checkpoint_task.verification_streak == 0
        versions_before_ignored = {item.knowledge_point: item.version for item in first.abilities}

        for status in (EvaluationStatus.REVIEW_PENDING, EvaluationStatus.DISPUTED):
            ignored_interview = await _seed_evaluation(
                sessions,
                knowledge_base_id=base.id,
                sequence=1,
                subtopic_key="checkpoint",
                subtopic_title="Checkpoint 与恢复",
                total=20,
                confidence=0.95,
                status=status,
            )
            ignored = await profiles.apply_interview_evaluations(ignored_interview)
            assert {item.knowledge_point: item.version for item in ignored.abilities} == (
                versions_before_ignored
            )

        async with sessions() as db:
            decisions = set(
                (
                    await db.scalars(
                        select(ProfileUpdateEventModel.decision).where(
                            ProfileUpdateEventModel.knowledge_base_id == base.id
                        )
                    )
                ).all()
            )
        assert {"skip_review_pending", "skip_disputed"}.issubset(decisions)

        low_confidence_interview = await _seed_evaluation(
            sessions,
            knowledge_base_id=base.id,
            sequence=1,
            subtopic_key="checkpoint",
            subtopic_title="Checkpoint 与恢复",
            total=18,
            confidence=0.50,
            status=EvaluationStatus.FINAL,
        )
        low_confidence = await profiles.apply_interview_evaluations(low_confidence_interview)
        checkpoint_ability = next(
            item
            for item in low_confidence.abilities
            if item.knowledge_point == "subtopic::langgraph::checkpoint"
        )
        assert checkpoint_ability.confidence_weighted_count == 1.5
        focuses = await profiles.training_focuses(DEFAULT_USER_ID, base.id)
        assert focuses[0].source_type == "review_task"

        for expected_streak in (1, 2):
            trusted_interview = await _seed_evaluation(
                sessions,
                knowledge_base_id=base.id,
                sequence=1,
                subtopic_key="checkpoint",
                subtopic_title="Checkpoint 与恢复",
                total=18,
                confidence=0.95,
                status=EvaluationStatus.FINAL,
            )
            verified = await profiles.apply_interview_evaluations(trusted_interview)
            task = next(item for item in verified.review_tasks if item.id == checkpoint_task.id)
            assert task.verification_streak == expected_streak
        assert task.status == ReviewTaskStatus.COMPLETED

        manual_interview = await _seed_evaluation(
            sessions,
            knowledge_base_id=base.id,
            sequence=1,
            subtopic_key="interrupt",
            subtopic_title="人工介入",
            total=4,
            confidence=0.95,
            status=EvaluationStatus.FINAL,
        )
        manual_snapshot = await profiles.apply_interview_evaluations(manual_interview)
        manual_task = next(
            task for task in manual_snapshot.review_tasks if task.subtopic_key == "interrupt"
        )
        assert manual_task.verification_streak == 0
        manually_closed = await profiles.complete_review_task(manual_task.id, base.id)
        assert manually_closed.status == ReviewTaskStatus.COMPLETED
        assert manually_closed.verification_streak == 0

        replay = await profiles.apply_interview_evaluations(low_interview)
        replayed_checkpoint = next(
            item for item in replay.abilities if item.id == checkpoint_ability.id
        )
        assert replayed_checkpoint.version == checkpoint_ability.version + 2

        isolated = await profiles.get_snapshot(DEFAULT_USER_ID, isolated_base.id)
        assert isolated.abilities == ()
        assert isolated.errors == ()
        assert isolated.review_tasks == ()
    finally:
        await engine.dispose()

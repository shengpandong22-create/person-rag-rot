from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.api.errors import AppError
from agent_mentor.domain.profile import (
    ReviewTaskStatus,
    classify_error,
    next_review_due,
    normalized_score,
    profile_update_decision,
    task_priority,
    updated_mastery,
)
from agent_mentor.infrastructure.database.models import (
    AbilityProfileModel,
    ErrorPatternModel,
    EvaluationModel,
    InterviewQuestionModel,
    InterviewSessionModel,
    ProfileUpdateEventModel,
    ReviewTaskModel,
    UserAnswerModel,
)


@dataclass(frozen=True, slots=True)
class ProfileSnapshot:
    abilities: tuple[AbilityProfileModel, ...]
    errors: tuple[ErrorPatternModel, ...]
    review_tasks: tuple[ReviewTaskModel, ...]


@dataclass(frozen=True, slots=True)
class RecommendedKnowledgePoint:
    knowledge_point: str
    reason: str
    priority: int
    mastery_score: float | None


class ProfileService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def apply_interview_evaluations(self, interview_id: UUID) -> ProfileSnapshot:
        async with self._sessions() as db:
            interview = await self._get_interview(db, interview_id)
            rows = await self._evaluation_rows(db, interview.id)
            for evaluation, question, answer in rows:
                existing = await db.scalar(
                    select(ProfileUpdateEventModel).where(
                        ProfileUpdateEventModel.evaluation_id == evaluation.id
                    )
                )
                if existing is None:
                    await self._apply_evaluation(
                        db,
                        user_id=interview.user_id,
                        evaluation=evaluation,
                        question=question,
                        answer=answer,
                    )
            await db.commit()
            return await self._snapshot(db, interview.user_id)

    async def get_snapshot(self, user_id: UUID) -> ProfileSnapshot:
        async with self._sessions() as db:
            return await self._snapshot(db, user_id)

    async def recommend_interview_plan(
        self, user_id: UUID, *, limit: int = 5
    ) -> tuple[RecommendedKnowledgePoint, ...]:
        snapshot = await self.get_snapshot(user_id)
        mastery_by_point = {
            ability.knowledge_point: ability.mastery_score for ability in snapshot.abilities
        }
        recommendations: list[RecommendedKnowledgePoint] = []
        open_tasks = [
            task for task in snapshot.review_tasks if task.status == ReviewTaskStatus.OPEN
        ]
        for task in sorted(open_tasks, key=lambda item: (-item.priority, item.due_at)):
            recommendations.append(
                RecommendedKnowledgePoint(
                    knowledge_point=task.knowledge_point,
                    reason=f"due_review_task:{task.error_type}",
                    priority=task.priority,
                    mastery_score=mastery_by_point.get(task.knowledge_point),
                )
            )
        recommended_points = {item.knowledge_point for item in recommendations}
        weak_abilities = sorted(snapshot.abilities, key=lambda item: item.mastery_score)
        for ability in weak_abilities:
            if ability.knowledge_point in recommended_points:
                continue
            recommendations.append(
                RecommendedKnowledgePoint(
                    knowledge_point=ability.knowledge_point,
                    reason="low_mastery",
                    priority=2 if ability.mastery_score < 0.7 else 1,
                    mastery_score=ability.mastery_score,
                )
            )
        return tuple(recommendations[:limit])

    async def complete_review_task(self, task_id: UUID) -> ReviewTaskModel:
        async with self._sessions() as db:
            task = await db.get(ReviewTaskModel, task_id)
            if task is None:
                raise AppError("REVIEW_TASK_NOT_FOUND", "Review task was not found.", 404)
            if task.status == ReviewTaskStatus.COMPLETED:
                return task
            task.status = ReviewTaskStatus.COMPLETED
            task.completed_at = datetime.now(UTC)
            task.updated_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(task)
            return task

    async def _apply_evaluation(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        evaluation: EvaluationModel,
        question: InterviewQuestionModel,
        answer: UserAnswerModel,
    ) -> None:
        decision = profile_update_decision(evaluation.status, evaluation.confidence)
        changes: dict[str, object] = {
            "evaluation_id": str(evaluation.id),
            "knowledge_points": question.knowledge_points,
            "decision": decision.reason,
        }
        if not decision.should_update:
            db.add(
                ProfileUpdateEventModel(
                    id=uuid4(),
                    evaluation_id=evaluation.id,
                    user_id=user_id,
                    decision=decision.reason,
                    applied=False,
                    changes=changes,
                    created_at=datetime.now(UTC),
                )
            )
            return

        score = normalized_score(evaluation.total)
        dimensions = {
            "correctness": evaluation.correctness,
            "completeness": evaluation.completeness,
            "reasoning": evaluation.reasoning,
            "communication": evaluation.communication,
        }
        changed_profiles: list[dict[str, object]] = []
        changed_errors: list[dict[str, object]] = []
        for point in question.knowledge_points or ["general"]:
            profile = await self._profile_for(db, user_id, point)
            old_mastery = profile.mastery_score
            profile.mastery_score = updated_mastery(
                profile.mastery_score,
                score,
                confidence_weight=decision.confidence_weight,
                difficulty=question.difficulty,
            )
            profile.confidence_weighted_count = round(
                profile.confidence_weighted_count + decision.confidence_weight, 4
            )
            profile.last_evaluation_id = evaluation.id
            profile.version += 1
            profile.updated_at = datetime.now(UTC)
            changed_profiles.append(
                {
                    "knowledge_point": point,
                    "old_mastery": old_mastery,
                    "new_mastery": profile.mastery_score,
                    "version": profile.version,
                }
            )
            error_type = classify_error(evaluation.total, dimensions, answer.answer_text)
            if error_type is not None:
                pattern = await self._record_error_pattern(
                    db,
                    user_id=user_id,
                    knowledge_point=point,
                    error_type=error_type,
                    evaluation=evaluation,
                )
                await self._upsert_review_task(
                    db,
                    user_id=user_id,
                    knowledge_point=point,
                    error_type=error_type,
                    evaluation=evaluation,
                    occurrence_count=pattern.occurrence_count,
                    mastery_score=profile.mastery_score,
                )
                changed_errors.append(
                    {
                        "knowledge_point": point,
                        "error_type": str(error_type),
                        "occurrence_count": pattern.occurrence_count,
                    }
                )
        changes["profiles"] = changed_profiles
        changes["errors"] = changed_errors
        db.add(
            ProfileUpdateEventModel(
                id=uuid4(),
                evaluation_id=evaluation.id,
                user_id=user_id,
                decision=decision.reason,
                applied=True,
                changes=changes,
                created_at=datetime.now(UTC),
            )
        )

    async def _profile_for(
        self, db: AsyncSession, user_id: UUID, knowledge_point: str
    ) -> AbilityProfileModel:
        profile = await db.scalar(
            select(AbilityProfileModel).where(
                AbilityProfileModel.user_id == user_id,
                AbilityProfileModel.knowledge_point == knowledge_point,
            )
        )
        if profile is not None:
            return profile
        now = datetime.now(UTC)
        profile = AbilityProfileModel(
            id=uuid4(),
            user_id=user_id,
            knowledge_point=knowledge_point,
            mastery_score=0.5,
            confidence_weighted_count=0,
            last_evaluation_id=None,
            version=0,
            created_at=now,
            updated_at=now,
        )
        db.add(profile)
        await db.flush()
        return profile

    async def _record_error_pattern(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        knowledge_point: str,
        error_type: str,
        evaluation: EvaluationModel,
    ) -> ErrorPatternModel:
        pattern = await db.scalar(
            select(ErrorPatternModel).where(
                ErrorPatternModel.user_id == user_id,
                ErrorPatternModel.knowledge_point == knowledge_point,
                ErrorPatternModel.error_type == error_type,
            )
        )
        now = datetime.now(UTC)
        if pattern is None:
            pattern = ErrorPatternModel(
                id=uuid4(),
                user_id=user_id,
                knowledge_point=knowledge_point,
                error_type=error_type,
                occurrence_count=1,
                first_seen_at=now,
                last_seen_at=now,
                last_evaluation_id=evaluation.id,
            )
            db.add(pattern)
            await db.flush()
            return pattern
        pattern.occurrence_count += 1
        pattern.last_seen_at = now
        pattern.last_evaluation_id = evaluation.id
        return pattern

    async def _upsert_review_task(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        knowledge_point: str,
        error_type: str,
        evaluation: EvaluationModel,
        occurrence_count: int,
        mastery_score: float,
    ) -> ReviewTaskModel:
        task = await db.scalar(
            select(ReviewTaskModel).where(
                ReviewTaskModel.user_id == user_id,
                ReviewTaskModel.knowledge_point == knowledge_point,
                ReviewTaskModel.error_type == error_type,
                ReviewTaskModel.status == ReviewTaskStatus.OPEN,
            )
        )
        now = datetime.now(UTC)
        due_at = next_review_due(now, occurrence_count)
        priority = task_priority(occurrence_count, mastery_score)
        if task is None:
            task = ReviewTaskModel(
                id=uuid4(),
                user_id=user_id,
                knowledge_point=knowledge_point,
                error_type=error_type,
                source_evaluation_id=evaluation.id,
                status=ReviewTaskStatus.OPEN,
                priority=priority,
                due_at=due_at,
                completed_at=None,
                created_at=now,
                updated_at=now,
            )
            db.add(task)
            await db.flush()
            return task
        task.source_evaluation_id = evaluation.id
        task.priority = max(task.priority, priority)
        task.due_at = due_at
        task.updated_at = now
        return task

    async def _evaluation_rows(
        self, db: AsyncSession, interview_id: UUID
    ) -> tuple[tuple[EvaluationModel, InterviewQuestionModel, UserAnswerModel], ...]:
        result = await db.execute(
            select(EvaluationModel, InterviewQuestionModel, UserAnswerModel)
            .join(
                InterviewQuestionModel,
                InterviewQuestionModel.id == EvaluationModel.question_id,
            )
            .join(UserAnswerModel, UserAnswerModel.id == EvaluationModel.answer_id)
            .where(InterviewQuestionModel.session_id == interview_id)
            .order_by(InterviewQuestionModel.sequence)
        )
        return tuple((row[0], row[1], row[2]) for row in result.all())

    async def _snapshot(self, db: AsyncSession, user_id: UUID) -> ProfileSnapshot:
        abilities = tuple(
            (
                await db.scalars(
                    select(AbilityProfileModel)
                    .where(AbilityProfileModel.user_id == user_id)
                    .order_by(AbilityProfileModel.knowledge_point)
                )
            ).all()
        )
        errors = tuple(
            (
                await db.scalars(
                    select(ErrorPatternModel)
                    .where(ErrorPatternModel.user_id == user_id)
                    .order_by(ErrorPatternModel.last_seen_at.desc())
                )
            ).all()
        )
        tasks = tuple(
            (
                await db.scalars(
                    select(ReviewTaskModel)
                    .where(ReviewTaskModel.user_id == user_id)
                    .order_by(ReviewTaskModel.status, ReviewTaskModel.due_at)
                )
            ).all()
        )
        return ProfileSnapshot(abilities=abilities, errors=errors, review_tasks=tasks)

    async def _get_interview(self, db: AsyncSession, interview_id: UUID) -> InterviewSessionModel:
        interview = await db.get(InterviewSessionModel, interview_id)
        if interview is None:
            raise AppError("INTERVIEW_NOT_FOUND", "Interview was not found.", 404)
        return interview

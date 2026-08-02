from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.api.errors import AppError
from agent_mentor.domain.profile import (
    ReviewTaskStatus,
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
from agent_mentor.domain.profile_taxonomy import (
    ProfileNode,
    canonical_subtopics,
    canonical_topic,
    routed_subtopic,
    routed_topic,
)
from agent_mentor.infrastructure.database.models import (
    AbilityProfileModel,
    ErrorPatternModel,
    EvaluationModel,
    InterviewQuestionModel,
    InterviewSessionModel,
    KnowledgeCatalogPointModel,
    KnowledgeCatalogSourceModel,
    ProfileUpdateEventModel,
    QuestionCoverageModel,
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
    topic_key: str | None
    topic_title: str | None
    subtopic_key: str | None
    subtopic_title: str | None
    reason: str
    priority: int
    mastery_score: float | None
    source_type: str = "profile"


@dataclass(frozen=True, slots=True)
class CoveragePoint:
    id: UUID
    title: str
    status: str
    source_count: int
    attempt_count: int
    trusted_evaluation_count: int
    average_score: float | None


@dataclass(frozen=True, slots=True)
class CoverageSnapshot:
    total: int
    uncovered: int
    attempted: int
    verified: int
    points: tuple[CoveragePoint, ...]


def _display_point(item: AbilityProfileModel | ReviewTaskModel) -> str:
    return item.subtopic_title or item.topic_title or item.knowledge_point


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
                        knowledge_base_id=interview.knowledge_base_id,
                        evaluation=evaluation,
                        question=question,
                        answer=answer,
                        interview_topic=interview.topic,
                        profile_topic_key=interview.profile_topic_key,
                        profile_topic_title=interview.profile_topic_title,
                        profile_subtopic_key=interview.profile_subtopic_key,
                        profile_subtopic_title=interview.profile_subtopic_title,
                    )
            await db.commit()
            return await self._snapshot(db, interview.user_id, interview.knowledge_base_id)

    async def backfill_two_layer_profiles(self, user_id: UUID) -> int:
        """Replay historical trusted evaluations once into the V2 hierarchy."""
        async with self._sessions() as db:
            result = await db.execute(
                select(
                    EvaluationModel,
                    InterviewQuestionModel,
                    UserAnswerModel,
                    InterviewSessionModel,
                    ProfileUpdateEventModel,
                )
                .join(
                    InterviewQuestionModel,
                    InterviewQuestionModel.id == EvaluationModel.question_id,
                )
                .join(UserAnswerModel, UserAnswerModel.id == EvaluationModel.answer_id)
                .join(
                    InterviewSessionModel,
                    InterviewSessionModel.id == InterviewQuestionModel.session_id,
                )
                .join(
                    ProfileUpdateEventModel,
                    ProfileUpdateEventModel.evaluation_id == EvaluationModel.id,
                )
                .where(InterviewSessionModel.user_id == user_id)
                .order_by(EvaluationModel.created_at, InterviewQuestionModel.sequence)
            )
            replayed = 0
            for evaluation, question, answer, interview, event in result.all():
                if event.changes.get("hierarchy_version") == 2:
                    continue
                await self._apply_evaluation(
                    db,
                    user_id=user_id,
                    knowledge_base_id=interview.knowledge_base_id,
                    evaluation=evaluation,
                    question=question,
                    answer=answer,
                    interview_topic=interview.topic,
                    profile_topic_key=interview.profile_topic_key,
                    profile_topic_title=interview.profile_topic_title,
                    profile_subtopic_key=interview.profile_subtopic_key,
                    profile_subtopic_title=interview.profile_subtopic_title,
                    existing_event=event,
                )
                replayed += 1
            await db.commit()
            return replayed

    async def get_snapshot(self, user_id: UUID, knowledge_base_id: UUID) -> ProfileSnapshot:
        async with self._sessions() as db:
            return await self._snapshot(db, user_id, knowledge_base_id)

    async def recommend_interview_plan(
        self, user_id: UUID, knowledge_base_id: UUID, *, limit: int = 5
    ) -> tuple[RecommendedKnowledgePoint, ...]:
        snapshot = await self.get_snapshot(user_id, knowledge_base_id)
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
                    knowledge_point=_display_point(task),
                    topic_key=task.topic_key,
                    topic_title=task.topic_title,
                    subtopic_key=task.subtopic_key,
                    subtopic_title=task.subtopic_title,
                    reason=f"due_review_task:{task.error_type}",
                    priority=task.priority,
                    mastery_score=mastery_by_point.get(task.knowledge_point),
                    source_type="review_task",
                )
            )
        coverage = await self.get_coverage(knowledge_base_id)
        for point in coverage.points:
            if point.status not in {"uncovered", "attempted", "insufficient_evidence"}:
                continue
            recommendations.append(
                RecommendedKnowledgePoint(
                    knowledge_point=point.title,
                    topic_key=None,
                    topic_title=point.title,
                    subtopic_key=None,
                    subtopic_title=None,
                    reason=f"coverage_gap:{point.status}",
                    priority=3 if point.status == "uncovered" else 2,
                    mastery_score=point.average_score,
                    source_type="coverage_gap",
                )
            )
        recommended_points = {task.knowledge_point for task in open_tasks}
        weak_abilities = sorted(
            (item for item in snapshot.abilities if item.profile_level == "topic"),
            key=lambda item: item.mastery_score,
        )
        for ability in weak_abilities:
            if ability.mastery_score >= 0.72:
                continue
            if ability.knowledge_point in recommended_points:
                continue
            recommendations.append(
                RecommendedKnowledgePoint(
                    knowledge_point=_display_point(ability),
                    topic_key=ability.topic_key,
                    topic_title=ability.topic_title,
                    subtopic_key=ability.subtopic_key,
                    subtopic_title=ability.subtopic_title,
                    reason="low_mastery",
                    priority=2 if ability.mastery_score < 0.7 else 1,
                    mastery_score=ability.mastery_score,
                    source_type="ability",
                )
            )
        return tuple(recommendations[:limit])

    async def get_coverage(self, knowledge_base_id: UUID) -> CoverageSnapshot:
        async with self._sessions() as db:
            source_rows = (
                await db.execute(
                    select(
                        KnowledgeCatalogSourceModel.knowledge_point_id,
                        func.count(KnowledgeCatalogSourceModel.id),
                    )
                    .join(
                        KnowledgeCatalogPointModel,
                        KnowledgeCatalogPointModel.id
                        == KnowledgeCatalogSourceModel.knowledge_point_id,
                    )
                    .where(KnowledgeCatalogPointModel.knowledge_base_id == knowledge_base_id)
                    .group_by(KnowledgeCatalogSourceModel.knowledge_point_id)
                )
            ).all()
            source_counts: dict[UUID, int] = {
                point_id: int(count) for point_id, count in source_rows
            }
            points = list(
                (
                    await db.scalars(
                        select(KnowledgeCatalogPointModel)
                        .where(
                            KnowledgeCatalogPointModel.knowledge_base_id == knowledge_base_id,
                            KnowledgeCatalogPointModel.id.in_(
                                tuple(source_counts) or (UUID(int=0),)
                            ),
                        )
                        .order_by(KnowledgeCatalogPointModel.title)
                    )
                ).all()
            )
            question_rows = (
                await db.execute(
                    select(
                        QuestionCoverageModel.knowledge_point_id, QuestionCoverageModel.question_id
                    ).where(
                        QuestionCoverageModel.knowledge_point_id.in_(
                            tuple(source_counts) or (UUID(int=0),)
                        )
                    )
                )
            ).all()
            attempts: dict[UUID, set[UUID]] = {}
            for point_id, question_id in question_rows:
                attempts.setdefault(point_id, set()).add(question_id)
            evaluation_rows = (
                await db.execute(
                    select(
                        QuestionCoverageModel.knowledge_point_id,
                        EvaluationModel.total,
                        EvaluationModel.confidence,
                        EvaluationModel.status,
                    )
                    .join(
                        EvaluationModel,
                        EvaluationModel.question_id == QuestionCoverageModel.question_id,
                    )
                    .where(
                        QuestionCoverageModel.knowledge_point_id.in_(
                            tuple(source_counts) or (UUID(int=0),)
                        )
                    )
                )
            ).all()
            trusted: dict[UUID, list[float]] = {}
            for point_id, total, confidence, status in evaluation_rows:
                if str(status) == "final" and confidence >= 0.70:
                    trusted.setdefault(point_id, []).append(total / 20)
            result: list[CoveragePoint] = []
            for point in points:
                scores = trusted.get(point.id, [])
                attempt_count = len(attempts.get(point.id, set()))
                average = round(sum(scores) / len(scores), 4) if scores else None
                if attempt_count == 0:
                    status = "uncovered"
                elif not scores:
                    status = "attempted"
                elif len(scores) < 2:
                    status = "insufficient_evidence"
                elif average is not None and average >= 0.80:
                    status = "mastered"
                elif average is not None and average < 0.70:
                    status = "weak"
                else:
                    status = "verified"
                result.append(
                    CoveragePoint(
                        id=point.id,
                        title=point.title,
                        status=status,
                        source_count=source_counts.get(point.id, 0),
                        attempt_count=attempt_count,
                        trusted_evaluation_count=len(scores),
                        average_score=average,
                    )
                )
            status_order = {
                "uncovered": 0,
                "attempted": 1,
                "insufficient_evidence": 2,
                "weak": 3,
                "verified": 4,
                "mastered": 5,
            }
            result.sort(key=lambda item: (status_order[item.status], item.title))
            return CoverageSnapshot(
                total=len(result),
                uncovered=sum(item.status == "uncovered" for item in result),
                attempted=sum(
                    item.status in {"attempted", "insufficient_evidence"} for item in result
                ),
                verified=sum(item.status in {"verified", "mastered"} for item in result),
                points=tuple(result),
            )

    async def training_focuses(
        self, user_id: UUID, knowledge_base_id: UUID, *, limit: int = 5
    ) -> tuple[RecommendedKnowledgePoint, ...]:
        snapshot = await self.get_snapshot(user_id, knowledge_base_id)
        mastery_by_point = {
            ability.knowledge_point: ability.mastery_score for ability in snapshot.abilities
        }
        candidates: list[TrainingFocusCandidate] = []
        for task in snapshot.review_tasks:
            if task.status != ReviewTaskStatus.OPEN:
                continue
            candidates.append(
                TrainingFocusCandidate(
                    knowledge_point=_display_point(task),
                    topic_key=task.topic_key,
                    topic_title=task.topic_title,
                    subtopic_key=task.subtopic_key,
                    subtopic_title=task.subtopic_title,
                    reason=f"专项复习任务：{task.error_type}",
                    priority=task.priority,
                    mastery_score=mastery_by_point.get(task.knowledge_point),
                    source_type="review_task",
                )
            )
        for ability in snapshot.abilities:
            if ability.profile_level != "topic":
                continue
            if ability.mastery_score >= 0.72:
                continue
            candidates.append(
                TrainingFocusCandidate(
                    knowledge_point=_display_point(ability),
                    topic_key=ability.topic_key,
                    topic_title=ability.topic_title,
                    subtopic_key=ability.subtopic_key,
                    subtopic_title=ability.subtopic_title,
                    reason="能力画像掌握度偏低",
                    priority=3 if ability.mastery_score < 0.45 else 2,
                    mastery_score=ability.mastery_score,
                    source_type="ability",
                )
            )
        return tuple(
            RecommendedKnowledgePoint(
                knowledge_point=item.knowledge_point,
                topic_key=item.topic_key,
                topic_title=item.topic_title,
                subtopic_key=item.subtopic_key,
                subtopic_title=item.subtopic_title,
                reason=item.reason,
                priority=item.priority,
                mastery_score=item.mastery_score,
                source_type=item.source_type,
            )
            for item in rank_training_focuses(candidates, limit=limit)
        )

    async def complete_review_task(self, task_id: UUID, knowledge_base_id: UUID) -> ReviewTaskModel:
        async with self._sessions() as db:
            task = await db.get(ReviewTaskModel, task_id)
            if task is None:
                raise AppError("REVIEW_TASK_NOT_FOUND", "Review task was not found.", 404)
            if task.knowledge_base_id != knowledge_base_id:
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
        knowledge_base_id: UUID,
        evaluation: EvaluationModel,
        question: InterviewQuestionModel,
        answer: UserAnswerModel,
        interview_topic: str,
        profile_topic_key: str | None = None,
        profile_topic_title: str | None = None,
        profile_subtopic_key: str | None = None,
        profile_subtopic_title: str | None = None,
        existing_event: ProfileUpdateEventModel | None = None,
    ) -> None:
        decision = profile_update_decision(evaluation.status, evaluation.confidence)
        topic = (
            routed_topic(profile_topic_key, profile_topic_title)
            if profile_topic_key and profile_topic_title
            else canonical_topic(interview_topic)
        )
        if profile_subtopic_key and profile_subtopic_title:
            subtopics = (routed_subtopic(topic, profile_subtopic_key, profile_subtopic_title),)
        else:
            subtopics = canonical_subtopics(
                topic,
                [interview_topic, *question.knowledge_points],
                question_type=question.question_type,
            )
        changes: dict[str, object] = {
            "evaluation_id": str(evaluation.id),
            "hierarchy_version": 2,
            "raw_knowledge_points": question.knowledge_points,
            "topic": topic.topic_key,
            "subtopics": [item.subtopic_key for item in subtopics],
            "decision": decision.reason,
        }
        if not decision.should_update:
            if existing_event is None:
                db.add(
                    ProfileUpdateEventModel(
                        id=uuid4(),
                        evaluation_id=evaluation.id,
                        user_id=user_id,
                        knowledge_base_id=knowledge_base_id,
                        decision=decision.reason,
                        applied=False,
                        changes=changes,
                        created_at=datetime.now(UTC),
                    )
                )
            else:
                existing_event.changes = changes
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
        nodes = (topic, *subtopics)
        for node in nodes:
            profile = await self._profile_for(db, user_id, knowledge_base_id, node)
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
                    "knowledge_point": node.display_title,
                    "profile_level": node.profile_level,
                    "old_mastery": old_mastery,
                    "new_mastery": profile.mastery_score,
                    "version": profile.version,
                }
            )
            error_type = classify_error(evaluation.total, dimensions, answer.answer_text)
            if error_type is not None and node.profile_level == "subtopic":
                pattern = await self._record_error_pattern(
                    db,
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                    node=node,
                    error_type=error_type,
                    evaluation=evaluation,
                )
                await self._upsert_review_task(
                    db,
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                    node=node,
                    error_type=error_type,
                    evaluation=evaluation,
                    occurrence_count=pattern.occurrence_count,
                    mastery_score=profile.mastery_score,
                )
                changed_errors.append(
                    {
                        "knowledge_point": node.display_title,
                        "error_type": str(error_type),
                        "occurrence_count": pattern.occurrence_count,
                    }
                )
        await self._advance_review_tasks(
            db,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            topic=topic,
            subtopics=subtopics,
            evaluation=evaluation,
            decision_should_update=decision.should_update,
        )
        changes["profiles"] = changed_profiles
        changes["errors"] = changed_errors
        if existing_event is None:
            db.add(
                ProfileUpdateEventModel(
                    id=uuid4(),
                    evaluation_id=evaluation.id,
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                    decision=decision.reason,
                    applied=True,
                    changes=changes,
                    created_at=datetime.now(UTC),
                )
            )
        else:
            existing_event.decision = decision.reason
            existing_event.applied = True
            existing_event.changes = changes

    async def _profile_for(
        self, db: AsyncSession, user_id: UUID, knowledge_base_id: UUID, node: ProfileNode
    ) -> AbilityProfileModel:
        profile = await db.scalar(
            select(AbilityProfileModel).where(
                AbilityProfileModel.user_id == user_id,
                AbilityProfileModel.knowledge_base_id == knowledge_base_id,
                AbilityProfileModel.knowledge_point == node.storage_key,
            )
        )
        if profile is not None:
            return profile
        now = datetime.now(UTC)
        profile = AbilityProfileModel(
            id=uuid4(),
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            knowledge_point=node.storage_key,
            profile_level=node.profile_level,
            topic_key=node.topic_key,
            topic_title=node.topic_title,
            subtopic_key=node.subtopic_key,
            subtopic_title=node.subtopic_title,
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
        knowledge_base_id: UUID,
        node: ProfileNode,
        error_type: str,
        evaluation: EvaluationModel,
    ) -> ErrorPatternModel:
        pattern = await db.scalar(
            select(ErrorPatternModel).where(
                ErrorPatternModel.user_id == user_id,
                ErrorPatternModel.knowledge_base_id == knowledge_base_id,
                ErrorPatternModel.knowledge_point == node.storage_key,
                ErrorPatternModel.error_type == error_type,
            )
        )
        now = datetime.now(UTC)
        if pattern is None:
            pattern = ErrorPatternModel(
                id=uuid4(),
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                knowledge_point=node.storage_key,
                profile_level=node.profile_level,
                topic_key=node.topic_key,
                topic_title=node.topic_title,
                subtopic_key=node.subtopic_key,
                subtopic_title=node.subtopic_title,
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
        knowledge_base_id: UUID,
        node: ProfileNode,
        error_type: str,
        evaluation: EvaluationModel,
        occurrence_count: int,
        mastery_score: float,
    ) -> ReviewTaskModel:
        task = await db.scalar(
            select(ReviewTaskModel).where(
                ReviewTaskModel.user_id == user_id,
                ReviewTaskModel.knowledge_base_id == knowledge_base_id,
                ReviewTaskModel.knowledge_point == node.storage_key,
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
                knowledge_base_id=knowledge_base_id,
                knowledge_point=node.storage_key,
                profile_level=node.profile_level,
                topic_key=node.topic_key,
                topic_title=node.topic_title,
                subtopic_key=node.subtopic_key,
                subtopic_title=node.subtopic_title,
                error_type=error_type,
                source_evaluation_id=evaluation.id,
                status=ReviewTaskStatus.OPEN,
                priority=priority,
                verification_streak=0,
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
        task.verification_streak = 0
        task.due_at = due_at
        task.updated_at = now
        return task

    async def _advance_review_tasks(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        knowledge_base_id: UUID,
        topic: ProfileNode,
        subtopics: tuple[ProfileNode, ...],
        evaluation: EvaluationModel,
        decision_should_update: bool,
    ) -> None:
        if not decision_should_update:
            return
        matching_subtopics = {item.subtopic_key for item in subtopics}
        tasks = (
            await db.scalars(
                select(ReviewTaskModel).where(
                    ReviewTaskModel.user_id == user_id,
                    ReviewTaskModel.knowledge_base_id == knowledge_base_id,
                    ReviewTaskModel.topic_key == topic.topic_key,
                    ReviewTaskModel.status == ReviewTaskStatus.OPEN,
                )
            )
        ).all()
        is_trusted_high = evaluation.confidence >= 0.70 and evaluation.total >= 16
        now = datetime.now(UTC)
        for task in tasks:
            if task.subtopic_key and task.subtopic_key not in matching_subtopics:
                continue
            streak, priority, completed = review_verification_progress(
                task.verification_streak,
                task.priority,
                trusted_high_score=is_trusted_high,
            )
            task.verification_streak = streak
            task.priority = priority
            task.updated_at = now
            if completed:
                task.status = ReviewTaskStatus.COMPLETED
                task.completed_at = now

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

    async def _snapshot(
        self, db: AsyncSession, user_id: UUID, knowledge_base_id: UUID
    ) -> ProfileSnapshot:
        abilities = tuple(
            (
                await db.scalars(
                    select(AbilityProfileModel)
                    .where(
                        AbilityProfileModel.user_id == user_id,
                        AbilityProfileModel.knowledge_base_id == knowledge_base_id,
                        AbilityProfileModel.profile_level.in_(("topic", "subtopic")),
                    )
                    .order_by(AbilityProfileModel.knowledge_point)
                )
            ).all()
        )
        errors = tuple(
            (
                await db.scalars(
                    select(ErrorPatternModel)
                    .where(
                        ErrorPatternModel.user_id == user_id,
                        ErrorPatternModel.knowledge_base_id == knowledge_base_id,
                        ErrorPatternModel.profile_level == "subtopic",
                    )
                    .order_by(ErrorPatternModel.last_seen_at.desc())
                )
            ).all()
        )
        tasks = tuple(
            (
                await db.scalars(
                    select(ReviewTaskModel)
                    .where(
                        ReviewTaskModel.user_id == user_id,
                        ReviewTaskModel.knowledge_base_id == knowledge_base_id,
                        ReviewTaskModel.profile_level.in_(("topic", "subtopic")),
                    )
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

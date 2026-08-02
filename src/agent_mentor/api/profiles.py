from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agent_mentor.application.knowledge_service import DEFAULT_USER_ID
from agent_mentor.application.profile_service import (
    CoverageSnapshot,
    ProfileService,
    ProfileSnapshot,
    RecommendedKnowledgePoint,
)
from agent_mentor.infrastructure.database.models import (
    AbilityProfileModel,
    ErrorPatternModel,
    ReviewTaskModel,
)

router = APIRouter(prefix="/api/v1", tags=["profiles"])


class AbilityResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    knowledge_point: str
    profile_level: str
    topic_key: str | None
    topic_title: str | None
    subtopic_key: str | None
    subtopic_title: str | None
    mastery_score: float
    confidence_weighted_count: float
    last_evaluation_id: UUID | None
    version: int
    updated_at: datetime


class ErrorPatternResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    knowledge_point: str
    profile_level: str
    topic_key: str | None
    topic_title: str | None
    subtopic_key: str | None
    subtopic_title: str | None
    error_type: str
    occurrence_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    last_evaluation_id: UUID


class ReviewTaskResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    knowledge_point: str
    profile_level: str
    topic_key: str | None
    topic_title: str | None
    subtopic_key: str | None
    subtopic_title: str | None
    error_type: str
    source_evaluation_id: UUID
    status: str
    priority: int
    verification_streak: int
    due_at: datetime
    completed_at: datetime | None


class ProfileSnapshotResponse(BaseModel):
    abilities: list[AbilityResponse]
    error_patterns: list[ErrorPatternResponse]
    review_tasks: list[ReviewTaskResponse]


class RecommendedKnowledgePointResponse(BaseModel):
    knowledge_point: str
    topic_key: str | None
    topic_title: str | None
    subtopic_key: str | None
    subtopic_title: str | None
    reason: str
    priority: int
    mastery_score: float | None
    source_type: str = "profile"


class CoveragePointResponse(BaseModel):
    id: UUID
    title: str
    status: str
    source_count: int
    attempt_count: int
    trusted_evaluation_count: int
    average_score: float | None


class CoverageSnapshotResponse(BaseModel):
    total: int
    uncovered: int
    attempted: int
    verified: int
    points: list[CoveragePointResponse]


def service(request: Request) -> ProfileService:
    return request.app.state.profile_service


def ability_response(profile: AbilityProfileModel) -> AbilityResponse:
    return AbilityResponse(
        id=profile.id,
        knowledge_base_id=profile.knowledge_base_id,
        knowledge_point=profile.knowledge_point,
        profile_level=profile.profile_level,
        topic_key=profile.topic_key,
        topic_title=profile.topic_title,
        subtopic_key=profile.subtopic_key,
        subtopic_title=profile.subtopic_title,
        mastery_score=profile.mastery_score,
        confidence_weighted_count=profile.confidence_weighted_count,
        last_evaluation_id=profile.last_evaluation_id,
        version=profile.version,
        updated_at=profile.updated_at,
    )


def error_response(pattern: ErrorPatternModel) -> ErrorPatternResponse:
    return ErrorPatternResponse(
        id=pattern.id,
        knowledge_base_id=pattern.knowledge_base_id,
        knowledge_point=pattern.knowledge_point,
        profile_level=pattern.profile_level,
        topic_key=pattern.topic_key,
        topic_title=pattern.topic_title,
        subtopic_key=pattern.subtopic_key,
        subtopic_title=pattern.subtopic_title,
        error_type=str(pattern.error_type),
        occurrence_count=pattern.occurrence_count,
        first_seen_at=pattern.first_seen_at,
        last_seen_at=pattern.last_seen_at,
        last_evaluation_id=pattern.last_evaluation_id,
    )


def task_response(task: ReviewTaskModel) -> ReviewTaskResponse:
    return ReviewTaskResponse(
        id=task.id,
        knowledge_base_id=task.knowledge_base_id,
        knowledge_point=task.knowledge_point,
        profile_level=task.profile_level,
        topic_key=task.topic_key,
        topic_title=task.topic_title,
        subtopic_key=task.subtopic_key,
        subtopic_title=task.subtopic_title,
        error_type=str(task.error_type),
        source_evaluation_id=task.source_evaluation_id,
        status=str(task.status),
        priority=task.priority,
        verification_streak=task.verification_streak,
        due_at=task.due_at,
        completed_at=task.completed_at,
    )


def snapshot_response(snapshot: ProfileSnapshot) -> ProfileSnapshotResponse:
    return ProfileSnapshotResponse(
        abilities=[ability_response(item) for item in snapshot.abilities],
        error_patterns=[error_response(item) for item in snapshot.errors],
        review_tasks=[task_response(item) for item in snapshot.review_tasks],
    )


def recommendation_response(
    recommendation: RecommendedKnowledgePoint,
) -> RecommendedKnowledgePointResponse:
    return RecommendedKnowledgePointResponse(
        knowledge_point=recommendation.knowledge_point,
        topic_key=recommendation.topic_key,
        topic_title=recommendation.topic_title,
        subtopic_key=recommendation.subtopic_key,
        subtopic_title=recommendation.subtopic_title,
        reason=recommendation.reason,
        priority=recommendation.priority,
        mastery_score=recommendation.mastery_score,
        source_type=recommendation.source_type,
    )


def coverage_response(snapshot: CoverageSnapshot) -> CoverageSnapshotResponse:
    return CoverageSnapshotResponse(
        total=snapshot.total,
        uncovered=snapshot.uncovered,
        attempted=snapshot.attempted,
        verified=snapshot.verified,
        points=[
            CoveragePointResponse(
                id=item.id,
                title=item.title,
                status=item.status,
                source_count=item.source_count,
                attempt_count=item.attempt_count,
                trusted_evaluation_count=item.trusted_evaluation_count,
                average_score=item.average_score,
            )
            for item in snapshot.points
        ],
    )


@router.post("/interviews/{interview_id}/profile-updates", response_model=ProfileSnapshotResponse)
async def apply_interview_profile_updates(
    interview_id: UUID, request: Request
) -> ProfileSnapshotResponse:
    return snapshot_response(await service(request).apply_interview_evaluations(interview_id))


@router.get(
    "/knowledge-bases/{knowledge_base_id}/profile/abilities",
    response_model=list[AbilityResponse],
)
async def list_my_abilities(knowledge_base_id: UUID, request: Request) -> list[AbilityResponse]:
    snapshot = await service(request).get_snapshot(DEFAULT_USER_ID, knowledge_base_id)
    return [ability_response(item) for item in snapshot.abilities]


@router.get(
    "/knowledge-bases/{knowledge_base_id}/profile/error-patterns",
    response_model=list[ErrorPatternResponse],
)
async def list_my_error_patterns(
    knowledge_base_id: UUID, request: Request
) -> list[ErrorPatternResponse]:
    snapshot = await service(request).get_snapshot(DEFAULT_USER_ID, knowledge_base_id)
    return [error_response(item) for item in snapshot.errors]


@router.get(
    "/knowledge-bases/{knowledge_base_id}/review-tasks",
    response_model=list[ReviewTaskResponse],
)
async def list_review_tasks(knowledge_base_id: UUID, request: Request) -> list[ReviewTaskResponse]:
    snapshot = await service(request).get_snapshot(DEFAULT_USER_ID, knowledge_base_id)
    return [task_response(item) for item in snapshot.review_tasks]


@router.get(
    "/knowledge-bases/{knowledge_base_id}/interview-plan",
    response_model=list[RecommendedKnowledgePointResponse],
)
async def recommend_interview_plan(
    knowledge_base_id: UUID, request: Request
) -> list[RecommendedKnowledgePointResponse]:
    return [
        recommendation_response(item)
        for item in await service(request).recommend_interview_plan(
            DEFAULT_USER_ID, knowledge_base_id
        )
    ]


@router.get(
    "/knowledge-bases/{knowledge_base_id}/coverage",
    response_model=CoverageSnapshotResponse,
)
async def get_knowledge_coverage(
    knowledge_base_id: UUID, request: Request
) -> CoverageSnapshotResponse:
    return coverage_response(await service(request).get_coverage(knowledge_base_id))


@router.get(
    "/knowledge-bases/{knowledge_base_id}/training-focuses",
    response_model=list[RecommendedKnowledgePointResponse],
)
async def list_training_focuses(
    knowledge_base_id: UUID, request: Request
) -> list[RecommendedKnowledgePointResponse]:
    return [
        recommendation_response(item)
        for item in await service(request).training_focuses(DEFAULT_USER_ID, knowledge_base_id)
    ]


@router.post(
    "/knowledge-bases/{knowledge_base_id}/review-tasks/{task_id}/complete",
    response_model=ReviewTaskResponse,
)
async def complete_review_task(
    knowledge_base_id: UUID, task_id: UUID, request: Request
) -> ReviewTaskResponse:
    return task_response(await service(request).complete_review_task(task_id, knowledge_base_id))

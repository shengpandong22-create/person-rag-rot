from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agent_mentor.application.evaluation_service import (
    EvaluationItem,
    EvaluationService,
    ReportHistoryItem,
    ReportSnapshot,
    ScoreTrendPoint,
)
from agent_mentor.application.knowledge_service import DEFAULT_USER_ID

router = APIRouter(prefix="/api/v1", tags=["evaluations"])


class EvaluateRequest(BaseModel):
    reviewer_available: bool = True


class EvaluationResponse(BaseModel):
    id: UUID
    question_id: UUID
    answer_id: UUID
    sequence: int
    question_text: str
    question_type: str
    difficulty: str
    knowledge_points: list[str]
    user_answer: str
    correctness: int
    completeness: int
    reasoning: int
    communication: int
    total: int
    confidence: float
    covered_points: list[str]
    missing_points: list[str]
    incorrect_claims: list[str]
    answer_evidence: list[str]
    reference_chunk_ids: list[UUID]
    feedback: str
    follow_up_recommended: bool
    needs_review: bool
    reviewed: bool
    review_reasons: list[str]
    review_decision: str
    status: str
    model_name: str
    prompt_version: str


class ReportResponse(BaseModel):
    id: UUID
    session_id: UUID
    total_score: int
    max_score: int
    dimension_summary: dict[str, object]
    knowledge_point_summary: dict[str, object]
    error_summary: list[str]
    low_confidence_items: list[str]
    disputed_items: list[str]
    next_steps: list[str]
    evaluations: list[EvaluationResponse]


class ReportHistoryResponse(BaseModel):
    id: UUID
    session_id: UUID
    topic: str
    difficulty: str
    total_score: int
    max_score: int
    score_ratio: float
    low_confidence_count: int
    disputed_count: int
    created_at: str


class ScoreTrendResponse(BaseModel):
    report_id: UUID
    session_id: UUID
    topic: str
    difficulty: str
    total_score: int
    max_score: int
    score_ratio: float
    dimension_averages: dict[str, float]
    created_at: str


def service(request: Request) -> EvaluationService:
    return request.app.state.evaluation_service


def evaluation_response(item: EvaluationItem) -> EvaluationResponse:
    evaluation = item.evaluation
    question = item.question
    answer = item.answer
    return EvaluationResponse(
        id=evaluation.id,
        question_id=evaluation.question_id,
        answer_id=evaluation.answer_id,
        sequence=question.sequence,
        question_text=question.question_text,
        question_type=str(question.question_type),
        difficulty=str(question.difficulty),
        knowledge_points=question.knowledge_points,
        user_answer=answer.answer_text,
        correctness=evaluation.correctness,
        completeness=evaluation.completeness,
        reasoning=evaluation.reasoning,
        communication=evaluation.communication,
        total=evaluation.total,
        confidence=evaluation.confidence,
        covered_points=evaluation.covered_points,
        missing_points=evaluation.missing_points,
        incorrect_claims=evaluation.incorrect_claims,
        answer_evidence=evaluation.answer_evidence,
        reference_chunk_ids=list(item.reference_chunk_ids),
        feedback=evaluation.feedback,
        follow_up_recommended=evaluation.follow_up_recommended,
        needs_review=evaluation.needs_review,
        reviewed=evaluation.reviewed,
        review_reasons=evaluation.review_reasons,
        review_decision=str(evaluation.review_decision),
        status=str(evaluation.status),
        model_name=evaluation.model_name,
        prompt_version=evaluation.prompt_version,
    )


def report_response(snapshot: ReportSnapshot) -> ReportResponse:
    report = snapshot.report
    return ReportResponse(
        id=report.id,
        session_id=report.session_id,
        total_score=report.total_score,
        max_score=report.max_score,
        dimension_summary=report.dimension_summary,
        knowledge_point_summary=report.knowledge_point_summary,
        error_summary=report.error_summary,
        low_confidence_items=report.low_confidence_items,
        disputed_items=report.disputed_items,
        next_steps=report.next_steps,
        evaluations=[evaluation_response(item) for item in snapshot.evaluations],
    )


def history_response(item: ReportHistoryItem) -> ReportHistoryResponse:
    report = item.report
    return ReportHistoryResponse(
        id=report.id,
        session_id=report.session_id,
        topic=item.interview.topic,
        difficulty=str(item.interview.difficulty),
        total_score=report.total_score,
        max_score=report.max_score,
        score_ratio=round(report.total_score / max(1, report.max_score), 4),
        low_confidence_count=len(report.low_confidence_items),
        disputed_count=len(report.disputed_items),
        created_at=report.created_at.isoformat(),
    )


def trend_response(item: ScoreTrendPoint) -> ScoreTrendResponse:
    return ScoreTrendResponse(
        report_id=item.report_id,
        session_id=item.session_id,
        topic=item.topic,
        difficulty=str(item.difficulty),
        total_score=item.total_score,
        max_score=item.max_score,
        score_ratio=item.score_ratio,
        dimension_averages=item.dimension_averages,
        created_at=item.created_at.isoformat(),
    )


@router.get("/reports/history", response_model=list[ReportHistoryResponse])
async def list_report_history(request: Request, limit: int = 10) -> list[ReportHistoryResponse]:
    return [
        history_response(item)
        for item in await service(request).list_report_history(DEFAULT_USER_ID, limit=limit)
    ]


@router.get("/reports/trends", response_model=list[ScoreTrendResponse])
async def list_score_trends(request: Request, limit: int = 10) -> list[ScoreTrendResponse]:
    return [
        trend_response(item)
        for item in await service(request).score_trends(DEFAULT_USER_ID, limit=limit)
    ]


@router.post(
    "/interviews/{interview_id}/evaluations",
    response_model=list[EvaluationResponse],
)
async def evaluate_interview(
    interview_id: UUID, payload: EvaluateRequest, request: Request
) -> list[EvaluationResponse]:
    items = await service(request).evaluate_interview(
        interview_id, reviewer_available=payload.reviewer_available
    )
    return [evaluation_response(item) for item in items]


@router.get(
    "/interviews/{interview_id}/evaluations",
    response_model=list[EvaluationResponse],
)
async def list_evaluations(interview_id: UUID, request: Request) -> list[EvaluationResponse]:
    return [
        evaluation_response(item) for item in await service(request).list_evaluations(interview_id)
    ]


@router.post("/interviews/{interview_id}/report", response_model=ReportResponse)
async def build_report(
    interview_id: UUID, payload: EvaluateRequest, request: Request
) -> ReportResponse:
    return report_response(
        await service(request).build_report(
            interview_id, reviewer_available=payload.reviewer_available
        )
    )


@router.get("/interviews/{interview_id}/report", response_model=ReportResponse)
async def get_report(interview_id: UUID, request: Request) -> ReportResponse:
    return report_response(await service(request).get_report(interview_id))

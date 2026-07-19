from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agent_mentor.application.evaluation_service import (
    EvaluationItem,
    EvaluationService,
    ReportSnapshot,
)

router = APIRouter(prefix="/api/v1", tags=["evaluations"])


class EvaluateRequest(BaseModel):
    reviewer_available: bool = True


class EvaluationResponse(BaseModel):
    id: UUID
    question_id: UUID
    answer_id: UUID
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


def service(request: Request) -> EvaluationService:
    return request.app.state.evaluation_service


def evaluation_response(item: EvaluationItem) -> EvaluationResponse:
    evaluation = item.evaluation
    return EvaluationResponse(
        id=evaluation.id,
        question_id=evaluation.question_id,
        answer_id=evaluation.answer_id,
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

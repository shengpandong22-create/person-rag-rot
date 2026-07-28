from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent_mentor.application.interview_service import (
    InterviewService,
    InterviewSnapshot,
    WorkflowTraceItem,
)
from agent_mentor.domain.interview import Difficulty
from agent_mentor.infrastructure.database.models import InterviewQuestionModel, UserAnswerModel

router = APIRouter(prefix="/api/v1", tags=["interviews"])


class InterviewCreateRequest(BaseModel):
    knowledge_base_id: UUID
    topic: str = Field(min_length=1, max_length=160)
    difficulty: Difficulty = Difficulty.MEDIUM
    question_count: int = Field(default=3, ge=1, le=10)


class InterviewQuestionResponse(BaseModel):
    id: UUID
    sequence: int
    question_text: str
    question_type: str
    difficulty: str
    reference_answer: str
    rubric: dict[str, object]
    reference_chunk_ids: list[UUID]
    placeholder_feedback: str | None


class UserAnswerResponse(BaseModel):
    id: UUID
    question_id: UUID
    answer_text: str
    answer_kind: str
    idempotency_key: str


class InterviewResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    topic: str
    difficulty: str
    question_count: int
    status: str
    current_question_index: int
    workflow_thread_id: str
    current_question: InterviewQuestionResponse | None
    answers: list[UserAnswerResponse]


class WorkflowTraceResponse(BaseModel):
    checkpoint_id: UUID
    node: str
    event: str
    label: str
    input_summary: str
    output_summary: str
    waiting_for_answer: bool
    is_fallback: bool
    error_message: str | None
    created_at: str


class AnswerSubmitRequest(BaseModel):
    question_id: UUID
    answer: str = Field(min_length=1, max_length=8000)


def service(request: Request) -> InterviewService:
    return request.app.state.interview_service


def question_response(
    question: InterviewQuestionModel | None, reference_chunk_ids: tuple[UUID, ...]
) -> InterviewQuestionResponse | None:
    if question is None:
        return None
    return InterviewQuestionResponse(
        id=question.id,
        sequence=question.sequence,
        question_text=question.question_text,
        question_type=str(question.question_type),
        difficulty=str(question.difficulty),
        reference_answer=question.reference_answer,
        rubric=question.rubric,
        reference_chunk_ids=list(reference_chunk_ids),
        placeholder_feedback=question.placeholder_feedback,
    )


def answer_response(answer: UserAnswerModel) -> UserAnswerResponse:
    return UserAnswerResponse(
        id=answer.id,
        question_id=answer.question_id,
        answer_text=answer.answer_text,
        answer_kind=str(answer.answer_kind),
        idempotency_key=answer.idempotency_key,
    )


def interview_response(snapshot: InterviewSnapshot) -> InterviewResponse:
    session = snapshot.session
    return InterviewResponse(
        id=session.id,
        knowledge_base_id=session.knowledge_base_id,
        topic=session.topic,
        difficulty=str(session.difficulty),
        question_count=session.question_count,
        status=str(session.status),
        current_question_index=session.current_question_index,
        workflow_thread_id=session.workflow_thread_id,
        current_question=question_response(
            snapshot.current_question, snapshot.current_reference_chunk_ids
        ),
        answers=[answer_response(answer) for answer in snapshot.answers],
    )


def workflow_trace_response(item: WorkflowTraceItem) -> WorkflowTraceResponse:
    return WorkflowTraceResponse(
        checkpoint_id=item.checkpoint_id,
        node=item.node,
        event=item.event,
        label=item.label,
        input_summary=item.input_summary,
        output_summary=item.output_summary,
        waiting_for_answer=item.waiting_for_answer,
        is_fallback=item.is_fallback,
        error_message=item.error_message,
        created_at=item.created_at.isoformat(),
    )


@router.post("/interviews", response_model=InterviewResponse, status_code=201)
async def create_interview(payload: InterviewCreateRequest, request: Request) -> InterviewResponse:
    session = await service(request).create_interview(
        knowledge_base_id=payload.knowledge_base_id,
        topic=payload.topic,
        difficulty=payload.difficulty,
        question_count=payload.question_count,
    )
    return interview_response(InterviewSnapshot(session, None, (), ()))


@router.post("/interviews/{interview_id}/start", response_model=InterviewResponse)
async def start_interview(interview_id: UUID, request: Request) -> InterviewResponse:
    return interview_response(await service(request).start(interview_id))


@router.get("/interviews/{interview_id}", response_model=InterviewResponse)
async def get_interview(interview_id: UUID, request: Request) -> InterviewResponse:
    return interview_response(await service(request).get(interview_id))


@router.get("/interviews/{interview_id}/workflow-trace", response_model=list[WorkflowTraceResponse])
async def get_workflow_trace(interview_id: UUID, request: Request) -> list[WorkflowTraceResponse]:
    trace = await service(request).workflow_trace(interview_id)
    return [workflow_trace_response(item) for item in trace]


@router.post("/interviews/{interview_id}/answers", response_model=InterviewResponse)
async def submit_answer(
    interview_id: UUID,
    payload: AnswerSubmitRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> InterviewResponse:
    return interview_response(
        await service(request).submit_answer(
            session_id=interview_id,
            question_id=payload.question_id,
            answer_text=payload.answer,
            idempotency_key=idempotency_key,
        )
    )


@router.get("/interviews/{interview_id}/events")
async def interview_events(interview_id: UUID, request: Request) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        async for item in service(request).events(interview_id):
            data = json.dumps(item["data"], ensure_ascii=False)
            yield f"event: {item['event']}\ndata: {data}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")

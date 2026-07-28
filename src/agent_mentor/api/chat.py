from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent_mentor.application.answer_service import AnswerResult, AnswerService
from agent_mentor.ports.knowledge_retriever import RetrievalQuery, RetrievedChunk

router = APIRouter(prefix="/api/v1", tags=["chat"])


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=20)
    candidate_k: int = Field(default=20, ge=1, le=100)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    candidate_k: int | None = Field(default=None, ge=1, le=100)
    allow_model_knowledge: bool = False


class RetrievedChunkResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    source_url: str | None
    trust_level: str
    heading_path: list[str]
    page_number: int | None
    block_type: str
    chunk_index: int
    content: str
    score: float
    retrieval_explanation: str
    vector_rank: int | None
    text_rank: int | None
    vector_score: float | None
    text_score: float | None


class AskResponse(BaseModel):
    session_id: UUID
    message_id: UUID
    answer: str
    evidence_sufficient: bool
    generation_mode: str
    model_name: str | None
    fallback_reason: str | None
    citations: list[RetrievedChunkResponse]
    candidates: list[RetrievedChunkResponse]


def answer_service(request: Request) -> AnswerService:
    return request.app.state.answer_service


def chunk_response(chunk: RetrievedChunk) -> RetrievedChunkResponse:
    return RetrievedChunkResponse(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        document_title=chunk.document_title,
        source_url=chunk.source_url,
        trust_level=chunk.trust_level,
        heading_path=list(chunk.heading_path),
        page_number=chunk.page_number,
        block_type=chunk.block_type,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        score=chunk.score,
        retrieval_explanation=chunk.retrieval_explanation,
        vector_rank=chunk.vector_rank,
        text_rank=chunk.text_rank,
        vector_score=chunk.vector_score,
        text_score=chunk.text_score,
    )


def ask_response(result: AnswerResult) -> AskResponse:
    return AskResponse(
        session_id=result.session_id,
        message_id=result.message_id,
        answer=result.answer,
        evidence_sufficient=result.evidence_sufficient,
        generation_mode=result.generation_mode,
        model_name=result.model_name,
        fallback_reason=result.fallback_reason,
        citations=[chunk_response(chunk) for chunk in result.citations],
        candidates=[chunk_response(chunk) for chunk in result.candidates],
    )


@router.post(
    "/knowledge-bases/{knowledge_base_id}/retrieve", response_model=list[RetrievedChunkResponse]
)
async def retrieve(
    knowledge_base_id: UUID, payload: RetrievalRequest, request: Request
) -> list[RetrievedChunkResponse]:
    results = await request.app.state.knowledge_retriever.retrieve(
        RetrievalQuery(
            knowledge_base_id=knowledge_base_id,
            query=payload.query,
            top_k=payload.top_k,
            candidate_k=payload.candidate_k,
        )
    )
    return [chunk_response(chunk) for chunk in results]


@router.post("/knowledge-bases/{knowledge_base_id}/ask", response_model=AskResponse)
async def ask(knowledge_base_id: UUID, payload: AskRequest, request: Request) -> AskResponse:
    result = await answer_service(request).answer(
        knowledge_base_id=knowledge_base_id,
        question=payload.question,
        top_k=payload.top_k,
        candidate_k=payload.candidate_k,
        allow_model_knowledge=payload.allow_model_knowledge,
    )
    return ask_response(result)


@router.post("/knowledge-bases/{knowledge_base_id}/ask/stream")
async def ask_stream(
    knowledge_base_id: UUID, payload: AskRequest, request: Request
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        async for item in answer_service(request).answer_events(
            knowledge_base_id=knowledge_base_id,
            question=payload.question,
            top_k=payload.top_k,
            candidate_k=payload.candidate_k,
            allow_model_knowledge=payload.allow_model_knowledge,
        ):
            data = json.dumps(item["data"], ensure_ascii=False)
            yield f"event: {item['event']}\ndata: {data}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")

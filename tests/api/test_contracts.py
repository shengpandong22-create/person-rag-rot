from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from agent_mentor.api.errors import AppError
from agent_mentor.application.answer_service import AnswerResult
from agent_mentor.application.evaluation_service import ReportSnapshot
from agent_mentor.infrastructure.database.models import InterviewReportModel
from agent_mentor.ports.knowledge_retriever import RetrievedChunk


class _FailingInterviewService:
    async def start(self, _interview_id: UUID) -> object:
        raise AppError("INTERVIEW_NOT_FOUND", "Interview was not found.", 404)


class _AnswerService:
    async def answer(
        self,
        *,
        knowledge_base_id: UUID,
        question: str,
        top_k: int | None,
        candidate_k: int | None,
        allow_model_knowledge: bool,
    ) -> AnswerResult:
        del knowledge_base_id, question, top_k, candidate_k, allow_model_knowledge
        chunk = RetrievedChunk(
            chunk_id=uuid4(),
            document_id=uuid4(),
            document_title="RAG 学习资料",
            source_url=None,
            trust_level="internal",
            heading_path=("RAG", "引用边界"),
            page_number=None,
            block_type="paragraph",
            chunk_index=1,
            content="RAG 回答必须基于检索证据，并返回可校验引用。",
            score=0.91,
            retrieval_explanation="RRF=0.0325 vector_rank=1 text_rank=2",
            vector_rank=1,
            text_rank=2,
            vector_score=0.87,
            text_score=0.66,
        )
        return AnswerResult(
            session_id=uuid4(),
            message_id=uuid4(),
            answer="RAG 回答需要基于证据，并携带引用。",
            citations=(chunk,),
            candidates=(chunk,),
            evidence_sufficient=True,
            generation_mode="llm",
            model_name="deepseek-chat",
            fallback_reason=None,
        )


class _EvaluationService:
    async def build_report(
        self, _interview_id: UUID, *, reviewer_available: bool
    ) -> ReportSnapshot:
        del reviewer_available
        report = SimpleNamespace(
            id=uuid4(),
            session_id=uuid4(),
            total_score=0,
            max_score=0,
            dimension_summary={},
            knowledge_point_summary={"topic": "RAG"},
            error_summary=[],
            low_confidence_items=[],
            disputed_items=[],
            next_steps=["完成面试后继续训练。"],
        )
        return ReportSnapshot(report=cast(InterviewReportModel, report), evaluations=())


def test_api_validation_errors_use_stable_error_contract(app: Any) -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/interviews",
        json={"knowledge_base_id": str(uuid4()), "topic": "RAG", "question_count": 0},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["trace_id"]


def test_submit_answer_requires_idempotency_key_header(app: Any) -> None:
    client = TestClient(app)

    response = client.post(
        f"/api/v1/interviews/{uuid4()}/answers",
        json={"question_id": str(uuid4()), "answer": "RAG 需要引用证据。"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_app_error_is_mapped_to_uniform_response_body(app: Any) -> None:
    app.state.interview_service = _FailingInterviewService()
    client = TestClient(app)

    response = client.post(f"/api/v1/interviews/{uuid4()}/start", json={})

    assert response.status_code == 404
    assert response.json() == {
        "code": "INTERVIEW_NOT_FOUND",
        "message": "Interview was not found.",
        "detail": None,
        "trace_id": response.json()["trace_id"],
    }


def test_ask_endpoint_preserves_grounded_answer_contract(app: Any) -> None:
    app.state.answer_service = _AnswerService()
    client = TestClient(app)

    response = client.post(
        f"/api/v1/knowledge-bases/{uuid4()}/ask",
        json={"question": "RAG 为什么需要引用？", "top_k": 3, "candidate_k": 10},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["evidence_sufficient"] is True
    assert body["generation_mode"] == "llm"
    assert body["fallback_reason"] is None
    assert len(body["citations"]) == 1
    assert body["citations"][0]["retrieval_explanation"].startswith("RRF=")
    assert len(body["candidates"]) == 1


def test_report_endpoint_allows_empty_evaluation_list_contract(app: Any) -> None:
    app.state.evaluation_service = _EvaluationService()
    client = TestClient(app)

    response = client.post(
        f"/api/v1/interviews/{uuid4()}/report",
        json={"reviewer_available": True},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["total_score"] == 0
    assert body["max_score"] == 0
    assert body["evaluations"] == []
    assert body["next_steps"] == ["完成面试后继续训练。"]

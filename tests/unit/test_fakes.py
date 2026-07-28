from __future__ import annotations

import math

import pytest
from pydantic import BaseModel

from agent_mentor.infrastructure.embedding import DevelopmentEmbeddingGateway
from agent_mentor.infrastructure.fakes import FakeEmbeddingGateway, FakeLLMGateway
from agent_mentor.ports.llm_gateway import Message, ModelPolicy, TraceContext


class ExampleResponse(BaseModel):
    value: str


@pytest.mark.asyncio
async def test_fake_llm_returns_configured_response_and_records_call() -> None:
    fake = FakeLLMGateway(structured_responses=[{"value": "configured"}])
    trace_context = TraceContext(trace_id="trace-123", operation="test")

    response = await fake.generate_structured(
        operation="test",
        messages=[Message(role="user", content="hello")],
        response_model=ExampleResponse,
        model_policy=ModelPolicy(),
        trace_context=trace_context,
    )

    assert response == ExampleResponse(value="configured")
    assert fake.calls[0].trace_context == trace_context
    assert fake.calls[0].messages[0].content == "hello"


@pytest.mark.asyncio
async def test_fake_embedding_is_deterministic_and_records_batches() -> None:
    fake = FakeEmbeddingGateway(dimension=3)

    first = await fake.embed_documents(["Java", "RAG"])
    second = await fake.embed_query("Java")

    assert len(first) == 2
    assert len(first[0]) == 3
    assert first[0] == second
    assert fake.document_calls == [("Java", "RAG")]
    assert fake.query_calls == ["Java"]


@pytest.mark.asyncio
async def test_development_embedding_preserves_lexical_similarity() -> None:
    gateway = DevelopmentEmbeddingGateway(dimension=256)
    query = await gateway.embed_query("LangGraph 状态持久化和 checkpoint")
    related, unrelated = await gateway.embed_documents(
        [
            "LangGraph 使用 checkpoint 持久化工作流状态，支持中断恢复。",
            "PostgreSQL 事务隔离级别和索引执行计划。",
        ]
    )

    def cosine(left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right, strict=True)) / (
            math.sqrt(sum(value * value for value in left))
            * math.sqrt(sum(value * value for value in right))
        )

    assert cosine(query, related) > cosine(query, unrelated)
    assert math.isclose(sum(value * value for value in query), 1.0, rel_tol=1e-6)

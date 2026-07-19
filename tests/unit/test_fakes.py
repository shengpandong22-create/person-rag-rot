from __future__ import annotations

import pytest
from pydantic import BaseModel

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

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from agent_mentor.domain.users import User
from agent_mentor.ports.embedding_gateway import EmbeddingGateway
from agent_mentor.ports.knowledge_retriever import (
    KnowledgeRetriever,
    RetrievalQuery,
    RetrievedChunk,
)
from agent_mentor.ports.llm_gateway import LLMGateway, Message, ModelPolicy, TraceContext
from agent_mentor.ports.repositories import UserRepository


@dataclass(frozen=True, slots=True)
class FakeLLMCall:
    operation: str
    messages: tuple[Message, ...]
    trace_context: TraceContext


@dataclass(slots=True)
class FakeLLMGateway(LLMGateway):
    """Deterministic test adapter that records every call."""

    structured_responses: list[BaseModel | dict[str, Any]] = field(default_factory=list)
    text_responses: list[str] = field(default_factory=list)
    calls: list[FakeLLMCall] = field(default_factory=list)

    async def generate_structured(
        self,
        *,
        operation: str,
        messages: Sequence[Message],
        response_model: type[BaseModel],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
    ) -> BaseModel:
        del model_policy
        self.calls.append(FakeLLMCall(operation, tuple(messages), trace_context))
        if not self.structured_responses:
            raise RuntimeError("FakeLLMGateway has no configured structured response")
        response = self.structured_responses.pop(0)
        if isinstance(response, response_model):
            return response
        return response_model.model_validate(response)

    async def stream_text(
        self,
        *,
        operation: str,
        messages: Sequence[Message],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
    ) -> AsyncIterator[str]:
        del model_policy
        self.calls.append(FakeLLMCall(operation, tuple(messages), trace_context))
        if not self.text_responses:
            raise RuntimeError("FakeLLMGateway has no configured text response")
        for token in self.text_responses.pop(0).split():
            yield token


@dataclass(slots=True)
class FakeEmbeddingGateway(EmbeddingGateway):
    dimension: int = 8
    document_calls: list[tuple[str, ...]] = field(default_factory=list)
    query_calls: list[str] = field(default_factory=list)

    def _vector_for(self, text: str) -> list[float]:
        seed = sum(ord(char) for char in text)
        return [float((seed + index) % 10) / 10 for index in range(self.dimension)]

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        self.document_calls.append(tuple(texts))
        return [self._vector_for(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return self._vector_for(text)


@dataclass(slots=True)
class FakeKnowledgeRetriever(KnowledgeRetriever):
    results: list[RetrievedChunk] = field(default_factory=list)
    calls: list[RetrievalQuery] = field(default_factory=list)

    async def retrieve(self, query: RetrievalQuery) -> list[RetrievedChunk]:
        self.calls.append(query)
        return self.results[: query.top_k]


@dataclass(slots=True)
class InMemoryUserRepository(UserRepository):
    users_by_email: dict[str, User] = field(default_factory=dict)

    async def add(self, user: User) -> None:
        self.users_by_email[user.email] = user

    async def get_by_email(self, email: str) -> User | None:
        return self.users_by_email.get(email)

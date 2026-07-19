from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ModelPolicy:
    model: str | None = None
    timeout_seconds: float = 30.0
    max_retries: int = 2


@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: str
    operation: str


class LLMGateway(Protocol):
    async def generate_structured(
        self,
        *,
        operation: str,
        messages: Sequence[Message],
        response_model: type[T],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
    ) -> T: ...

    def stream_text(
        self,
        *,
        operation: str,
        messages: Sequence[Message],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
    ) -> AsyncIterator[str]: ...


LLMResponse = BaseModel | dict[str, Any]

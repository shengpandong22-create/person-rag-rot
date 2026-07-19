from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from agent_mentor.ports.llm_gateway import LLMGateway, Message, ModelPolicy, TraceContext

T = TypeVar("T", bound=BaseModel)


class LLMGatewayError(RuntimeError):
    """Raised when the configured model endpoint cannot produce a valid response."""


@dataclass(frozen=True, slots=True)
class OpenAICompatibleLLMGateway(LLMGateway):
    """Small OpenAI-compatible adapter that works with DeepSeek and similar providers."""

    base_url: str
    api_key: str
    default_model: str

    async def generate_structured(
        self,
        *,
        operation: str,
        messages: Sequence[Message],
        response_model: type[T],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
    ) -> T:
        schema = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
        json_messages = [
            {
                "role": "system",
                "content": (
                    "你是 AgentMentor 的结构化输出模块。"
                    "只返回一个合法 JSON 对象，不要使用 Markdown。"
                    f"JSON Schema: {schema}"
                ),
            },
            *self._messages(messages),
        ]
        content = await self._complete(
            operation=operation,
            messages=json_messages,
            model_policy=model_policy,
            trace_context=trace_context,
            response_format={"type": "json_object"},
        )
        try:
            return response_model.model_validate_json(self._extract_json(content))
        except (ValidationError, ValueError) as error:
            raise LLMGatewayError(f"LLM structured output is invalid: {error}") from error

    def stream_text(
        self,
        *,
        operation: str,
        messages: Sequence[Message],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
    ) -> AsyncIterator[str]:
        async def iterator() -> AsyncIterator[str]:
            content = await self._complete(
                operation=operation,
                messages=self._messages(messages),
                model_policy=model_policy,
                trace_context=trace_context,
            )
            for token in content.split():
                yield token

        return iterator()

    async def _complete(
        self,
        *,
        operation: str,
        messages: list[dict[str, str]],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
        response_format: dict[str, str] | None = None,
    ) -> str:
        del operation
        payload: dict[str, Any] = {
            "model": model_policy.model or self.default_model,
            "messages": messages,
            "temperature": 0.2,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-AgentMentor-Trace-Id": trace_context.trace_id,
        }
        last_error: Exception | None = None
        for _attempt in range(model_policy.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=model_policy.timeout_seconds) as client:
                    response = await client.post(
                        f"{self.base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    if response.status_code == 400 and response_format is not None:
                        payload.pop("response_format", None)
                        response = await client.post(
                            f"{self.base_url.rstrip('/')}/chat/completions",
                            headers=headers,
                            json=payload,
                        )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise LLMGatewayError("LLM returned an empty message.")
                return content
            except Exception as error:  # noqa: BLE001 - gateway converts provider failures.
                last_error = error
        raise LLMGatewayError(f"LLM call failed after retries: {last_error}") from last_error

    def _messages(self, messages: Sequence[Message]) -> list[dict[str, str]]:
        return [{"role": item.role, "content": item.content} for item in messages]

    def _extract_json(self, content: str) -> str:
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No JSON object found in model output.")
        return stripped[start : end + 1]

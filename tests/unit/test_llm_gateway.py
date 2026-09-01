from __future__ import annotations

from typing import Any

import httpx
import pytest

from agent_mentor.infrastructure.llm import LLMGatewayError, OpenAICompatibleLLMGateway
from agent_mentor.ports.llm_gateway import ModelPolicy, TraceContext


def make_gateway() -> OpenAICompatibleLLMGateway:
    return OpenAICompatibleLLMGateway(
        base_url="https://provider.example/v1",
        api_key="sk-test",
        default_model="test-model",
    )


@pytest.mark.asyncio
async def test_non_retryable_client_error_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = make_gateway()
    calls = {"count": 0}

    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> httpx.Response:
        del self, kwargs
        calls["count"] += 1
        return httpx.Response(401, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(LLMGatewayError, match="failed fast"):
        await gateway._complete(
            operation="test",
            messages=[{"role": "user", "content": "hi"}],
            model_policy=ModelPolicy(max_retries=3),
            trace_context=TraceContext(trace_id="trace-1", operation="test"),
        )

    assert calls["count"] == 1
    await gateway.aclose()


@pytest.mark.asyncio
async def test_retryable_status_retries_with_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = make_gateway()
    calls = {"count": 0}
    sleeps: list[float] = []

    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> httpx.Response:
        del self, kwargs
        calls["count"] += 1
        return httpx.Response(429, request=httpx.Request("POST", url))

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr("asyncio.sleep", fake_sleep)

    with pytest.raises(LLMGatewayError, match="after retries"):
        await gateway._complete(
            operation="test",
            messages=[{"role": "user", "content": "hi"}],
            model_policy=ModelPolicy(max_retries=2),
            trace_context=TraceContext(trace_id="trace-1", operation="test"),
        )

    assert calls["count"] == 3
    assert sleeps == [0.25, 0.5]
    await gateway.aclose()


@pytest.mark.asyncio
async def test_json_object_fallback_reuses_request_without_response_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = make_gateway()
    payloads: list[dict[str, Any]] = []

    async def fake_post(self: httpx.AsyncClient, url: str, **kwargs: Any) -> httpx.Response:
        del self
        payload = kwargs["json"]
        payloads.append(dict(payload))
        if "response_format" in payload:
            return httpx.Response(400, request=httpx.Request("POST", url))
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await gateway._complete(
        operation="test",
        messages=[{"role": "user", "content": "hi"}],
        model_policy=ModelPolicy(max_retries=2),
        trace_context=TraceContext(trace_id="trace-1", operation="test"),
        response_format={"type": "json_object"},
    )

    assert result == "ok"
    assert "response_format" in payloads[0]
    assert "response_format" not in payloads[1]
    await gateway.aclose()

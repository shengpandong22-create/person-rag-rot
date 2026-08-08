"""OpenAI 兼容 LLM 网关 — 生产环境的 LLM 调用实现。

支持 DeepSeek 等所有 OpenAI-compatible API 的供应商。
核心特性：
    1. 结构化输出（generate_structured）：要求 LLM 返回符合 Pydantic 模型的 JSON
    2. 流式输出（stream_text）：逐 token 推送文本
    3. 自动降级：response_format 不兼容时自动去除后重试
    4. 重试机制：失败后按 max_retries 重试
    5. JSON 提取：能处理 LLM 返回的 Markdown 代码块包裹的 JSON
"""

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
    """LLM 调用失败异常 — 所有 LLM 相关错误统一包装为此类型"""


@dataclass(frozen=True, slots=True)
class OpenAICompatibleLLMGateway(LLMGateway):
    """OpenAI 兼容的 LLM 适配器 — 支持 DeepSeek 及所有兼容 API 的供应商。
    
    初始化参数：
        base_url:       API 地址，如 https://api.deepseek.com/v1
        api_key:        API 密钥
        default_model:  默认模型名，如 deepseek-chat
    """

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
        """结构化生成 — 要求 LLM 返回符合指定 Pydantic 模型的 JSON。
        
        流程：
            1. 将 response_model 的 JSON Schema 注入 system prompt
            2. 使用 response_format={"type": "json_object"} 强制 JSON 输出
            3. 从返回内容中提取 JSON（处理 Markdown 包裹情况）
            4. Pydantic 校验并返回结构化对象
            
        降级策略：
            - 如果 API 返回 400（不支持 json_object），自动去除 response_format 重试
            - JSON 提取失败 → 抛出 LLMGatewayError
            - Pydantic 校验失败 → 抛出 LLMGatewayError
        """
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
        """流式文本生成 — 返回异步迭代器，逐 token 推送。
        
        注意：当前实现是先获取完整内容再拆分，非真正的流式。
        如需真正的逐 token 流式，需改用 httpx 的 streaming 模式。
        """
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
        """底层调用 — 发送 chat/completions 请求，支持重试和降级。
        
        参数：
            response_format: 可选，{"type": "json_object"} 强制 JSON 输出
            
        容错机制：
            1. 如果 API 返回 400 且请求了 json_object → 去除 response_format 重试
            2. 按 max_retries 重试（共 max_retries+1 次尝试）
            3. 所有失败抛出 LLMGatewayError
            
        注意：temperature=0.2 固定，保证输出相对稳定
        """
        del operation  # operation 参数保留给子类或日志扩展
        payload: dict[str, Any] = {
            "model": model_policy.model or self.default_model,
            "messages": messages,
            "temperature": 0.2,  # 低温度，保证结构化输出的稳定性
        }
        if response_format is not None:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-AgentMentor-Trace-Id": trace_context.trace_id,  # 可观测性
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
                    # 降级：如果 API 不支持 json_object 格式，去除后重试
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
        """将内部 Message 列表转为 OpenAI API 格式"""
        return [{"role": item.role, "content": item.content} for item in messages]

    def _extract_json(self, content: str) -> str:
        """从 LLM 返回内容中提取 JSON 字符串。
        
        处理两种情况：
            1. 纯 JSON：{"answer": "..."}
            2. Markdown 代码块包裹：
               ```json
               {"answer": "..."}
               ```
        """
        stripped = content.strip()
        # 去除 Markdown 代码块标记
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
        # 找到第一个 { 到最后一个 } 之间的内容
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No JSON object found in model output.")
        return stripped[start : end + 1]

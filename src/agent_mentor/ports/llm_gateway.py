"""LLM 调用端口 — 定义与 LLM 交互的契约，业务层通过此接口调用大模型。

两种调用模式：
    1. generate_structured()：返回 Pydantic 结构化对象（评分、出题等场景）
    2. stream_text()：流式返回文本（逐字推送场景）

设计要点：
    - 业务层不直接依赖 OpenAI/DeepSeek SDK，通过此接口隔离供应商
    - ModelPolicy 封装重试和超时策略
    - TraceContext 贯穿每次调用，用于可观测性
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class Message:
    """单条对话消息，role 为 system/user/assistant"""
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ModelPolicy:
    """模型调用策略 — 控制调用行为和容错。
    
    timeout_seconds=30: 单次调用超时
    max_retries=2:      失败后最多重试 2 次（共 3 次尝试）
    """
    model: str | None = None  # None 则用 default_model
    timeout_seconds: float = 30.0
    max_retries: int = 2


@dataclass(frozen=True, slots=True)
class TraceContext:
    """调用追踪上下文 — 用于关联一次 LLM 调用到具体的请求/操作"""
    trace_id: str     # 唯一请求 ID，贯穿整个请求链路
    operation: str    # 操作名称，如 "rag_answer"、"interview_question"


class LLMGateway(Protocol):
    """LLM 网关接口（Protocol 协议类）。
    
    实现类：OpenAICompatibleLLMGateway（生产）、FakeLLMGateway（测试）
    """

    async def generate_structured(
        self,
        *,
        operation: str,
        messages: Sequence[Message],
        response_model: type[T],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
    ) -> T:
        """结构化生成 — 要求 LLM 返回符合 Pydantic 模型的结构化 JSON。
        
        典型场景：评分（EvaluationOutput）、出题（InterviewQuestionOutput）、
                 问答（GroundedAnswerOutput）
        """
        ...

    def stream_text(
        self,
        *,
        operation: str,
        messages: Sequence[Message],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
    ) -> AsyncIterator[str]:
        """流式文本生成 — 返回异步迭代器，逐 token 推送。
        
        典型场景：需要逐字展示给用户的场景（当前项目中暂未大规模使用）
        """
        ...


LLMResponse = BaseModel | dict[str, Any]

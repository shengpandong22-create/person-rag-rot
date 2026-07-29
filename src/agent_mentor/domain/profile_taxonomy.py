from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha1


@dataclass(frozen=True, slots=True)
class ProfileNode:
    profile_level: str
    topic_key: str
    topic_title: str
    subtopic_key: str | None = None
    subtopic_title: str | None = None

    @property
    def storage_key(self) -> str:
        if self.profile_level == "topic":
            return f"topic::{self.topic_key}"
        return f"subtopic::{self.topic_key}::{self.subtopic_key}"

    @property
    def display_title(self) -> str:
        return self.subtopic_title or self.topic_title


_TOPICS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("rag", "RAG", ("rag", "retrieval", "检索增强", "向量检索", "召回", "引用溯源")),
    (
        "langgraph",
        "LangGraph",
        ("langgraph", "stategraph", "checkpoint", "checkpointer", "状态图"),
    ),
    ("tool_calling", "Agent 工具调用", ("tool calling", "function calling", "工具调用", "mcp")),
    (
        "context_memory",
        "上下文与记忆管理",
        ("context", "memory", "token", "compact", "上下文", "记忆", "压缩"),
    ),
    (
        "agent_engineering",
        "AI Agent 工程化",
        ("agent", "工作流", "可观测", "评估", "guardrail", "工程化"),
    ),
)

_SUBTOPICS: dict[str, tuple[tuple[str, str, tuple[str, ...]], ...]] = {
    "rag": (
        ("retrieval", "检索与召回", ("retrieve", "retrieval", "query", "key", "召回", "检索")),
        ("citation", "证据引用", ("citation", "evidence", "引用", "证据", "溯源")),
        (
            "generation",
            "生成边界",
            ("generate", "generation", "value", "context", "生成", "上下文"),
        ),
        ("evaluation", "评估与可靠性", ("evaluate", "metric", "faithful", "评估", "准确", "幻觉")),
    ),
    "langgraph": (
        ("state", "状态建模", ("state", "reducer", "状态", "合并")),
        ("checkpoint", "Checkpoint 与恢复", ("checkpoint", "persist", "恢复", "持久化")),
        ("orchestration", "图编排", ("node", "edge", "graph", "节点", "边", "编排")),
        ("interrupt", "人工介入", ("interrupt", "human-in-the-loop", "中断", "人工介入")),
        ("streaming", "流式事件", ("stream", "writer", "event", "流式", "事件")),
    ),
}

_FALLBACK_SUBTOPICS: dict[str, tuple[str, str]] = {
    "concept": ("concept", "核心概念"),
    "scenario": ("engineering", "工程落地"),
    "tradeoff": ("tradeoff", "架构取舍"),
    "debug": ("recovery", "排障与恢复"),
}


def canonical_topic(raw_topic: str) -> ProfileNode:
    normalized = _normalized(raw_topic)
    for key, title, keywords in _TOPICS:
        if any(keyword in normalized for keyword in keywords):
            return ProfileNode("topic", key, title)
    title = _display_text(raw_topic) or "综合能力"
    key = _slug(title)
    return ProfileNode("topic", key, title)


def canonical_subtopics(
    topic: ProfileNode,
    raw_points: list[str],
    *,
    question_type: str,
) -> tuple[ProfileNode, ...]:
    definitions = _SUBTOPICS.get(topic.topic_key, ())
    matched: dict[str, ProfileNode] = {}
    for raw_point in raw_points:
        normalized = _normalized(raw_point)
        for key, title, keywords in definitions:
            if any(keyword in normalized for keyword in keywords):
                matched[key] = ProfileNode(
                    "subtopic",
                    topic.topic_key,
                    topic.topic_title,
                    key,
                    title,
                )
    if not matched:
        key, title = _fallback_subtopic(question_type)
        matched[key] = ProfileNode(
            "subtopic",
            topic.topic_key,
            topic.topic_title,
            key,
            title,
        )
    return tuple(matched.values())


def _fallback_subtopic(question_type: str) -> tuple[str, str]:
    normalized = _normalized(question_type)
    for marker, result in _FALLBACK_SUBTOPICS.items():
        if marker in normalized:
            return result
    return _FALLBACK_SUBTOPICS["concept"]


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _display_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())[:60]


def _slug(value: str) -> str:
    ascii_slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if ascii_slug:
        return ascii_slug[:48]
    # Unicode topics remain deterministic without exposing the full title as a storage key.
    return f"topic-{sha1(value.encode('utf-8')).hexdigest()[:10]}"

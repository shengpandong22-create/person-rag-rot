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
    (
        "java_backend",
        "Java 后端",
        ("java", "jvm", "spring", "happens-before", "线程池", "事务"),
    ),
    ("rag", "RAG", ("rag", "retrieval", "检索增强", "向量检索", "召回", "引用溯源")),
    (
        "langgraph",
        "LangGraph",
        ("langgraph", "stategraph", "checkpoint", "checkpointer", "状态图"),
    ),
    (
        "langchain",
        "LangChain",
        ("langchain", "create_agent", "agent middleware", "结构化输出"),
    ),
    (
        "tool_calling",
        "Agent 工具调用",
        ("tool calling", "function calling", "工具调用", "mcp"),
    ),
    (
        "context_memory",
        "上下文与记忆管理",
        ("context", "memory", "token", "compact", "上下文", "记忆", "压缩"),
    ),
    (
        "evaluation",
        "评估与可靠性",
        ("agent eval", "llm-as-judge", "评估与可靠性", "评测", "评估", "可靠性"),
    ),
    (
        "agent_engineering",
        "AI Agent 工程化",
        ("agent", "工作流", "可观测", "guardrail", "工程化", "生产部署"),
    ),
)

_SUBTOPICS: dict[str, tuple[tuple[str, str, tuple[str, ...]], ...]] = {
    "java_backend": (
        ("jvm", "JVM 与 GC", ("jvm", "gc", "垃圾回收", "类加载", "虚拟机")),
        ("concurrency", "Java 并发", ("concurrent", "volatile", "happens-before", "线程", "锁")),
        ("spring", "Spring 核心", ("spring", "ioc", "aop", "bean", "代理")),
        ("transaction", "事务与一致性", ("transaction", "事务", "隔离", "传播", "outbox")),
        ("production", "Java 服务生产化", ("actuator", "liveness", "readiness", "可观测", "生产")),
    ),
    "rag": (
        ("retrieval", "检索与召回", ("retrieve", "retrieval", "query", "key", "召回", "检索")),
        ("citation", "证据引用", ("citation", "evidence", "引用", "证据", "溯源")),
        ("generation", "生成边界", ("generate", "generation", "context", "生成", "上下文")),
        ("evaluation", "RAG 评估", ("faithful", "grounded", "准确", "幻觉", "评估")),
    ),
    "langgraph": (
        ("state", "状态建模", ("state", "reducer", "状态", "合并")),
        ("checkpoint", "Checkpoint 与恢复", ("checkpoint", "persist", "恢复", "持久化")),
        ("orchestration", "图编排", ("node", "edge", "graph", "节点", "边", "编排")),
        ("interrupt", "人工介入", ("interrupt", "human-in-the-loop", "中断", "人工介入")),
        ("streaming", "流式事件", ("stream", "writer", "event", "流式", "事件")),
    ),
    "langchain": (
        ("agent_runtime", "Agent 运行时", ("create_agent", "agent loop", "运行时", "代理循环")),
        ("middleware", "中间件", ("middleware", "中间件", "hook")),
        ("structured_output", "结构化输出", ("structured output", "schema", "结构化输出")),
    ),
    "tool_calling": (
        ("schema", "工具契约", ("schema", "参数", "契约", "description")),
        ("execution", "工具执行", ("execute", "execution", "调用", "执行")),
        ("mcp", "MCP 集成", ("mcp", "server", "client", "协议")),
        ("security", "工具安全", ("permission", "sandbox", "安全", "权限")),
    ),
    "context_memory": (
        ("short_term", "短期记忆", ("short-term", "thread", "短期", "会话记忆")),
        ("long_term", "长期记忆", ("long-term", "store", "长期", "跨会话")),
        ("context_engineering", "上下文工程", ("context engineering", "上下文工程", "上下文窗口")),
        ("compaction", "压缩与摘要", ("compact", "summary", "压缩", "摘要")),
    ),
    "evaluation": (
        ("dataset", "评测数据集", ("dataset", "test case", "数据集", "测试集")),
        ("metrics", "指标与评分", ("metric", "score", "rubric", "指标", "评分")),
        ("judge", "模型裁判", ("judge", "llm-as-judge", "裁判", "评审")),
        ("reliability", "可靠性治理", ("reliability", "fallback", "可靠", "降级")),
    ),
    "agent_engineering": (
        ("workflow", "工作流设计", ("workflow", "工作流", "编排")),
        ("observability", "可观测性", ("observability", "trace", "日志", "可观测")),
        ("guardrail", "安全护栏", ("guardrail", "安全", "护栏")),
        ("production", "生产化部署", ("production", "deploy", "生产", "部署")),
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
    return ProfileNode("topic", _slug(title), title)


def routed_topic(topic_key: str, topic_title: str) -> ProfileNode:
    """Build a stable topic from trusted profile routing metadata."""
    return ProfileNode("topic", topic_key, topic_title)


def routed_subtopic(topic: ProfileNode, subtopic_key: str, subtopic_title: str) -> ProfileNode:
    """Build a stable subtopic from trusted profile routing metadata."""
    return ProfileNode(
        "subtopic",
        topic.topic_key,
        topic.topic_title,
        subtopic_key,
        subtopic_title,
    )


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
    return f"topic-{sha1(value.encode('utf-8')).hexdigest()[:10]}"

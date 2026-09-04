# V3 改造计划：面试官 Agent 化（最小 Agent Loop）

> **前置条件**：一周硬伤改造计划（`one-week-hardening-plan-v1.md`）已完成并合入 main。
> 本计划在其基础上进行，gateway 已是"普通类 + 共享 AsyncClient"形态。
> 使用方式不变：每张任务卡整段复制给 ChatGPT，按 checkbox 执行。

**Goal**: 把"模拟面试官"从线性状态机升级为持有 3 个工具、每轮自主决策的真 Agent（tool-calling loop），让项目从"RAG 系统"变成"RAG + Agent 系统"。

**核心改造**: 现有 `submit_answer` 出下一题时，检索 query 是固定的（`interview_service.py:313` 的 topic + 题型 hint），**完全不看用户回答内容**。Agent 化后：面试官基于你的回答自主决定——是追问薄弱点、调画像换方向、还是结束本题。

**设计决策（开工前先给 ChatGPT 讲清楚）**:
- **不引入 LangChain/LangGraph**：OpenAI tool-calling 协议本身极简，自研 loop 200 行内，可观测性完全可控。这是面试话术，不是偷懒。
- **不动现有三题工作流**：`submit_answer` 原路径零改动，Agent 以"追问增强层"叠加。回归风险为零。
- **`AnswerKind` 可能已有 FOLLOWUP 值**：让 ChatGPT 先查 `domain/interview.py`，有就复用，没有就加枚举值 + Alembic（检查该列是否为 DB 枚举）。

**时间预算**: 3 晚，约 10 小时。

| 晚      | 时长 | 任务                               |
| ------- | ---- | ---------------------------------- |
| Night 1 | 3h   | Gateway 层 tool-calling 支持       |
| Night 2 | 4h   | InterviewerAgent 循环 + 三工具适配 |
| Night 3 | 3h   | API/SSE 集成 + 手工验收 + 话术     |

---

## Night 1（3h）：Gateway 层 Tool-Calling 支持

### 现状

`src/agent_mentor/ports/llm_gateway.py` 只有 `generate_structured` / `stream_text` / `stream_complete`，没有传 `tools` 参数、也没有返回 `tool_calls` 的能力。DeepSeek API 原生支持 OpenAI 格式的 function calling。

### 任务步骤

- [ ] **1.1 定义类型**（加进 `ports/llm_gateway.py`）：

```python
@dataclass(frozen=True, slots=True)
class ToolSpec:
    """工具声明 — 传给 LLM 的 function 定义（JSON Schema 参数）。"""
    name: str
    description: str
    parameters: dict[str, object]  # JSON Schema


@dataclass(frozen=True, slots=True)
class ToolCall:
    """LLM 返回的工具调用请求。"""
    id: str            # provider 返回的 call id，回传时必须带上
    name: str
    arguments: str     # 原始 JSON 字符串，由调用方解析


@dataclass(frozen=True, slots=True)
class ToolLoopMessage:
    """tool loop 中的消息（比 Message 多 tool_calls / tool_call_id 两种形态）。"""
    role: str                      # assistant | tool
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None  # role=tool 时必填
```

- [ ] **1.2 写失败测试**（`tests/unit/infrastructure/test_llm_gateway.py` 追加）：

```python
async def test_generate_with_tools_returns_tool_calls(monkeypatch):
    """LLM 决定调用工具时，gateway 应解析出 ToolCall 而不是文本。"""
    gateway = make_gateway()
    body = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "search_knowledge", "arguments": "{\"query\": \"HashMap 扩容\"}"},
                }],
            }
        }]
    }

    async def fake_post(self, url, **kwargs):  # noqa: ANN001
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    result = await gateway.generate_with_tools(
        operation="agent",
        messages=[Message(role="user", content="面试我")],
        tools=[ToolSpec(name="search_knowledge", description="搜资料",
                        parameters={"type": "object", "properties": {}})],
        model_policy=ModelPolicy(),
        trace_context=TraceContext(trace_id="t", operation="agent"),
    )
    assert result.role == "assistant"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search_knowledge"
    assert json.loads(result.tool_calls[0].arguments)["query"] == "HashMap 扩容"
```

- [ ] **1.3 跑测试确认失败**（方法不存在）

- [ ] **1.4 实现 `generate_with_tools`**（加进 `OpenAICompatibleLLMGateway`，Protocol 同步声明）：

```python
    async def generate_with_tools(
        self,
        *,
        operation: str,
        messages: Sequence[Message | ToolLoopMessage],
        tools: Sequence[ToolSpec],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
    ) -> ToolLoopMessage:
        """带工具声明的生成：LLM 可能返回文本，也可能返回 tool_calls。"""
        payload = {
            "model": model_policy.model or self._default_model,
            "messages": [self._loop_message(m) for m in messages],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ],
            "temperature": 0.2,
        }
        response = await self._post_json(payload, trace_context)
        message = response["choices"][0]["message"]
        calls = tuple(
            ToolCall(
                id=call["id"],
                name=call["function"]["name"],
                arguments=call["function"]["arguments"],
            )
            for call in message.get("tool_calls") or []
        )
        return ToolLoopMessage(
            role="assistant", content=message.get("content"), tool_calls=calls
        )

    def _loop_message(self, message: Message | ToolLoopMessage) -> dict[str, object]:
        if isinstance(message, ToolLoopMessage):
            if message.role == "assistant" and message.tool_calls:
                return {
                    "role": "assistant",
                    "content": message.content or None,
                    "tool_calls": [
                        {
                            "id": c.id,
                            "type": "function",
                            "function": {"name": c.name, "arguments": c.arguments},
                        }
                        for c in message.tool_calls
                    ],
                }
            return {
                "role": message.role,
                "content": message.content or "",
                **({"tool_call_id": message.tool_call_id} if message.tool_call_id else {}),
            }
        return {"role": message.role, "content": message.content}
```

注意：`_post_json` 是从 `_complete` 里抽出的"发 payload + 返回解析后 JSON"的公共私有方法（不带 response_format、不做重试循环改动，直接复用 `_complete` 的重试逻辑——可以让 ChatGPT 重构 `_complete` 内部为调用 `_post_json`，保持现有测试绿）。

- [ ] **1.5 测试 + 提交**：

```bash
python -m uv run pytest && git add -A && git commit -m "feat(llm): tool-calling support in gateway"
```

### 验收标准

- 单测证明：tool_calls 正确解析、无 tool_calls 时返回纯文本 assistant 消息、messages 往返序列化（assistant+tool 消息能传回 provider）
- 全量 pytest 绿

### 防坑清单

- `tool_call_id` 回传漏掉会收到 provider 400：`role=tool` 消息必须带 `tool_call_id`
- arguments 是**字符串**不是 dict（OpenAI 协议如此），解析放调用方
- Fake/Stub LLM（tests 里）若显式实现 Protocol，需要补 `generate_with_tools`

---

## Night 2（4h）：InterviewerAgent 循环 + 三工具适配

### 架构

```
新建 src/agent_mentor/agent/interviewer.py

InterviewerAgent
├── loop(): agent 主循环（max_steps 防失控）
├── 工具注册表: dict[name, Tool]（Tool = name + schema + async execute）
│   ├── search_knowledge(query)   → KnowledgeRetriever.retrieve（截断到 ~2000 字符）
│   ├── get_user_profile()        → ProfileService（返回掌握度摘要）
│   └── check_answer_quality(answer) → EvaluationService 评分逻辑（复用 evaluate_answer_direct 若 V2 已建，否则构造最小评分调用）
└── trace: 每步产出 AgentStepRecord（tool 名/参数摘要/结果摘要/耗时）
```

### 任务步骤

- [ ] **2.1 定义 Tool 协议**（`src/agent_mentor/agent/tools.py` 新建）：

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agent_mentor.ports.llm_gateway import ToolSpec


@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    value: Any  # 会被 json.dumps 后回传给 LLM


class Tool(Protocol):
    spec: ToolSpec

    async def execute(self, **kwargs: Any) -> ToolResult: ...
```

- [ ] **2.2 实现三个工具**（同文件或各自小文件，全部薄适配）：

```python
class SearchKnowledgeTool:
    def __init__(self, retriever: KnowledgeRetriever, knowledge_base_id: UUID) -> None:
        self._retriever = retriever
        self._kb_id = knowledge_base_id
        self.spec = ToolSpec(
            name="search_knowledge",
            description="在用户的学习资料库中检索与 query 相关的知识点，返回资料片段。出题或追问前应先调用。",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词，例如 'HashMap 扩容机制'"}
                },
                "required": ["query"],
            },
        )

    async def execute(self, *, query: str) -> ToolResult:
        chunks = await self._retriever.retrieve(
            RetrievalQuery(knowledge_base_id=self._kb_id, query=query, top_k=3, candidate_k=20)
        )
        # 截断防 token 爆炸
        value = [
            {"title": c.document_title, "content": c.content[:600]} for c in chunks
        ]
        return ToolResult(ok=True, value=value)
```

`GetUserProfileTool` / `CheckAnswerQualityTool` 同构：前者调 `ProfileService` 返回薄弱知识点列表（找到现有方法，如 `get_coverage` 或两轮画像的对外方法，让 ChatGPT 现场确认方法名）；后者复用评分逻辑返回四维分。**每个工具内部 try/except，失败返回 `ToolResult(ok=False, value=str(error))`，绝不让工具异常炸掉 loop。**

- [ ] **2.3 实现 Agent 循环**（`src/agent_mentor/agent/interviewer.py`）：

```python
AGENT_MAX_STEPS = 6
TOOL_RESULT_MAX_CHARS = 3000


@dataclass(frozen=True, slots=True)
class AgentStepRecord:
    step: int
    tool_name: str | None   # None = LLM 思考/最终回复
    arguments_summary: str
    result_summary: str
    duration_ms: int


class InterviewerAgent:
    def __init__(self, llm: LLMGateway, tools: Sequence[Tool], *, default_model: str | None) -> None:
        self._llm = llm
        self._tools = {t.spec.name: t for t in tools}
        self._default_model = default_model

    async def run(self, *, system_prompt: str, user_prompt: str) -> tuple[str, list[AgentStepRecord]]:
        """执行 agent loop，返回 (最终文本, 步骤轨迹)。"""
        messages: list[Message | ToolLoopMessage] = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]
        records: list[AgentStepRecord] = []
        for step in range(AGENT_MAX_STEPS):
            started = time.monotonic()
            reply = await self._llm.generate_with_tools(
                operation="interviewer_agent",
                messages=messages,
                tools=[t.spec for t in self._tools.values()],
                model_policy=ModelPolicy(model=self._default_model, timeout_seconds=60.0),
                trace_context=TraceContext(trace_id=str(uuid4()), operation="interviewer_agent"),
            )
            messages.append(reply)
            if not reply.tool_calls:
                records.append(AgentStepRecord(
                    step=step, tool_name=None, arguments_summary="",
                    result_summary=(reply.content or "")[:200],
                    duration_ms=int((time.monotonic() - started) * 1000),
                ))
                return reply.content or "", records  # loop 终止：LLM 给出最终回复
            for call in reply.tool_calls:
                records.append(await self._execute_tool(step, call))
                result = records[-1]
                messages.append(ToolLoopMessage(
                    role="tool",
                    content=result.result_summary[:TOOL_RESULT_MAX_CHARS],
                    tool_call_id=call.id,
                ))
        return "（达到最大推理步数，面试官请求中断本次追问。）", records

    async def _execute_tool(self, step: int, call: ToolCall) -> AgentStepRecord:
        started = time.monotonic()
        tool = self._tools.get(call.name)
        if tool is None:
            return AgentStepRecord(step, call.name, call.arguments[:100],
                                   f"unknown tool: {call.name}", 0)
        try:
            result = await tool.execute(**json.loads(call.arguments))
            value_str = json.dumps(result.value, ensure_ascii=False, default=str)
        except Exception as error:  # 工具失败不炸 loop
            value_str = json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False)
        return AgentStepRecord(
            step=step, tool_name=call.name,
            arguments_summary=call.arguments[:100],
            result_summary=value_str,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
```

- [ ] **2.4 Agent system prompt**（新建 `src/agent_mentor/prompts/interviewer_agent_v1.md`，代码里内嵌常量亦可）：

> 你是一名资深 AI/Java 面试官，正在面试一位 Java 后端转型的候选人。
> 流程规则：
> 1. 先调用 check_answer_quality 评估候选人刚给出的回答。
> 2. 若有明显薄弱点，调用 search_knowledge 检索相关资料，据此提出**一个**具体追问。
> 3. 若回答合格且已追问过一次，调用 get_user_profile 查看薄弱知识点，决定是否换方向出题。
> 4. 每次只输出一个动作；你的最终回复是给候选人看的一段话（追问或点评），不超过 150 字。
> 禁止：编造资料外结论；连续调用同一工具超过 2 次。

- [ ] **2.5 单测**（用 FakeLLM 脚本化 tool_calls 序列）：

- 场景 A：FakeLLM 第 1 轮返回 `check_answer_quality` 调用 → 工具执行 → 第 2 轮返回最终文本 → 断言 records 有 2 步、最终文本正确透传
- 场景 B：FakeLLM 调用不存在的工具 → loop 不崩，回传错误给 LLM
- 场景 C：FakeLLM 永远返回 tool_calls → max_steps 截断，返回兜底文案
- 场景 D：工具内部抛异常 → ToolResult(ok=False) 正常回传

- [ ] **2.6 测试 + 提交**：

```bash
python -m uv run pytest && git add -A && git commit -m "feat(agent): interviewer agent with tool-calling loop"
```

### 验收标准

- 四个场景单测全绿；现有全部测试不回归
- `InterviewerAgent.run` 不依赖 FastAPI Request（纯应用层，可独立测试）

### 防坑清单

- FakeLLM 的 `generate_with_tools` 要能按调用次数返回预设序列（用 `side_effect` 风格列表）
- `json.loads(call.arguments)` 可能炸（LLM 偶发输出非法 JSON）——`_execute_tool` 的 except 已兜住，确认测试覆盖
- 工具结果必须截断（`TOOL_RESULT_MAX_CHARS`），否则长资料会把上下文撑爆

---

## Night 3（3h）：API/SSE 集成 + 手工验收

### 任务步骤

- [ ] **3.1 组装**（`main.py`）：`app.state.interviewer_agent` 工厂——注意工具需要 `knowledge_base_id`，所以**按会话构建**：在 `InterviewService` 上加 `create_interviewer_agent(interview)` 方法，内部 new 一个绑定了当前 KB 和 profile 的 agent（每次追问请求构建，无状态，简单）。

- [ ] **3.2 追问 endpoint**（`api/interviews.py` 追加）：

```python
class FollowupRequest(BaseModel):
    question_id: UUID
    answer: str = Field(min_length=1, max_length=8000)


class AgentStepResponse(BaseModel):
    step: int
    tool_name: str | None
    arguments_summary: str
    result_summary: str
    duration_ms: int


class FollowupResponse(BaseModel):
    reply: str
    steps: list[AgentStepResponse]


@router.post("/interviews/{interview_id}/followup", response_model=FollowupResponse)
async def followup(interview_id: UUID, payload: FollowupRequest, request: Request) -> FollowupResponse:
    """面试官 Agent 基于候选人回答自主决定追问或点评。"""
    result = await service(request).agent_followup(
        session_id=interview_id, question_id=payload.question_id, answer=payload.answer
    )
    return FollowupResponse(reply=result.reply, steps=[AgentStepResponse(**s.__dict__) for s in result.steps])
```

- [ ] **3.3 `InterviewService.agent_followup`**：查 session/question → 构建 agent（绑定 KB）→ `run()` → 返回。**不改动现有状态机与 submit_answer**。追问记录可选入库（`AnswerKind.FOLLOWUP`，若枚举/表结构不允许则只返回不入库，记 TODO）。

- [ ] **3.4 手工验收**（真实 DeepSeek Key）：

```powershell
# 1. 创建并 start 一场面试（已有接口）
# 2. 对当前题目调用 followup，故意给一个半桶水回答
curl -X POST http://localhost:8000/api/v1/interviews/<id>/followup -H "Content-Type: application/json" -d '{"question_id": "<qid>", "answer": "RAG就是检索增强生成，先把文档存起来，回答的时候搜一下再喂给大模型"}'
```

验收要点（**这段体验就是面试演示素材**）：
- `steps` 里能看到 agent 自主调了 `check_answer_quality` → `search_knowledge` → 输出追问
- 追问内容引用了资料里的具体点（半桶水回答"存起来搜一下"→ 追问应指向分块策略/引用校验等未覆盖细节）
- 换一个高质量回答重试，agent 行为不同（点评而非硬追问）——**行为差异 = 自主决策的证据**

- [ ] **3.5 全量回归 + 提交 + 合并**：

```bash
python -m uv run pytest && python -m uv run pyright
git add -A && git commit -m "feat(api): interviewer agent followup endpoint with step trace"
```

- [ ] **3.6 更新 README 核心能力**（加一条）：“面试官 Agent：基于 tool-calling 的自主追问，决策轨迹可观测。”

- [ ] **3.7 面试话术（60 秒稿，背熟）**：

> "V2 之后我把面试官升级成了真正的 Agent：它持有三个工具——检索知识库、读用户画像、检查回答质量。每轮拿到候选人回答后，模型自主决定调用哪个工具、调几次，直到形成追问或点评，循环上限 6 步防失控，每一步的工具调用和耗时都落了 trace。我没用 LangChain，因为 tool-calling 协议本身很薄，自研 200 行反而让我能完全控制可观测性和上下文预算。最有说服力的演示是：给半桶水回答它会连查两步资料精准追问，给高质量回答它直接点评换方向——同一个 prompt，行为随输入分化，这就是 agent 和工作流的区别。"

### 防坑清单

- agent 每请求新建（无状态）是有意设计，V4 再考虑会话内记忆
- followup 的 answer 不带 idempotency（追问不落库就无所谓；落库则补 Idempotency-Key header）
- 若 DeepSeek 偶发不返回 tool_calls 直接给文本——这不是 bug，是模型判断无需调工具，正常返回即可

---

## 执行日志

| 日期    | 任务 | 实际耗时 | 测试 | 问题 |
| ------- | ---- | -------- | ---- | ---- |
| Night 1 |      |          |      |      |
| Night 2 |      |          |      |      |
| Night 3 |      |          |      |      |

## 与一周计划的衔接

- 本计划 **依赖** Day 1（gateway 类形态）和 Day 2（`_post_json` 抽取的基础），必须在其后执行
- 本计划 **不依赖** Day 4/5（BGE），无 Key 时 agent 走 fallback 无法演示，但单测不受影响
- 完成后回传：followup 接口的一次真实 steps 输出（JSON），用于下一轮锐评
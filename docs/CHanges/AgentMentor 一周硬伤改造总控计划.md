# AgentMentor 一周硬伤改造总控计划（20h / 6 晚 + 缓冲）

> **使用方式**：本计划由"监工"（Claude）产出，你在**能跑起来的那台电脑**上执行。
> 每晚开工时，把「本日任务卡」整段复制给 ChatGPT，按步骤执行；每完成一个 checkbox 就勾掉。
> 卡住超过 30 分钟，直接跳到本卡末尾的「防坑清单」对照排查。

**Goal**: 一周内闭环 5 个硬伤（伪流式 / 莽夫重试 / 假向量 / 无量化 eval / 工作流话术），让项目从"架构真、智能假"变成"每个卖点都有真实现 + 有数字"。

**总时间预算**: 20 小时（每晚清场后 2~4 小时，含 ChatGPT 辅助）

**执行环境前提**（开工前一次性确认，5 分钟）:
- [ ] 目标机器 `docker compose up -d --build` 能正常启动，http://localhost:8000/health/ready 返回 ok
- [ ] `.env` 已配置 DeepSeek Key（Day 2/3 真流式验证需要真实 LLM）
- [ ] `python -m uv run pytest` 全绿（记录通过数作为基线，记在本文末尾）
- [ ] 新建分支 `git checkout -b hardening-v2`，全部改造在此分支进行

**时间表总览**:

| 晚    | 时长 | 任务                                | 产出                               |
| ----- | ---- | ----------------------------------- | ---------------------------------- |
| Day 1 | 3h   | LLM Gateway 重试分级 + 连接复用     | 可重试错误有退避重试，4xx 快速失败 |
| Day 2 | 3h   | 真流式·网关层（httpx stream=True）  | gateway 真流式 API + 单测          |
| Day 3 | 2h   | 真流式·服务层（answer_events 改造） | SSE 首 token 延迟 ≈ 模型首 token   |
| Day 4 | 4h   | BGE·第一阶段（代码侧）              | BgeEmbeddingGateway 可用，单测绿   |
| Day 5 | 3h   | BGE·第二阶段（数据侧）              | 维度迁移 + 全量重嵌入 + 端到端验证 |
| Day 6 | 3h   | Eval Runner MVP + recall@k 报告     | 一份有数字的检索质量报告           |
| Day 7 | 2h   | 工作流话术 + 全量回归 + 收尾        | 面试叙事定稿，main 分支合并        |

---

## Day 1（3h）：LLM Gateway 重试分级 + 连接复用

### 现状与问题

`src/agent_mentor/infrastructure/llm.py:103-127` 的 `_complete`:
- 每次调用、每次重试都新建 `httpx.AsyncClient`（无连接复用）
- `except Exception` 一律重试：400/401/403 这种永远不可能成功的错误也会重试满次数
- 无退避、无抖动，重试风暴会打爆 provider
- `del operation`（llm.py:90）—— 参数收了没用

### 任务步骤

- [ ] **1.1 写失败测试**：在 `tests/unit/infrastructure/test_llm_gateway.py`（若无则新建）添加：

```python
import httpx
import pytest

from agent_mentor.infrastructure.llm import LLMGatewayError, OpenAICompatibleLLMGateway
from agent_mentor.ports.llm_gateway import ModelPolicy, TraceContext


def make_gateway() -> OpenAICompatibleLLMGateway:
    return OpenAICompatibleLLMGateway(
        base_url="http://fake", api_key="sk-test", default_model="test-model"
    )


async def test_non_retryable_error_fails_fast(monkeypatch):
    """401 不应触发重试——直接抛 LLMGatewayError。"""
    gateway = make_gateway()
    calls = {"count": 0}

    async def fake_post(self, url, **kwargs):  # noqa: ANN001
        calls["count"] += 1
        return httpx.Response(401, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    with pytest.raises(LLMGatewayError):
        await gateway._complete(
            operation="test",
            messages=[{"role": "user", "content": "hi"}],
            model_policy=ModelPolicy(max_retries=3),
            trace_context=TraceContext(trace_id="t", operation="test"),
        )
    assert calls["count"] == 1  # 快速失败，没有重试


async def test_retryable_error_retries_with_backoff(monkeypatch):
    """429 应重试 max_retries 次，且两次调用之间有 sleep。"""
    gateway = make_gateway()
    calls = {"count": 0}
    sleeps: list[float] = []

    async def fake_post(self, url, **kwargs):  # noqa: ANN001
        calls["count"] += 1
        return httpx.Response(429, request=httpx.Request("POST", url))

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr("asyncio.sleep", fake_sleep)
    with pytest.raises(LLMGatewayError):
        await gateway._complete(
            operation="test",
            messages=[{"role": "user", "content": "hi"}],
            model_policy=ModelPolicy(max_retries=2),
            trace_context=TraceContext(trace_id="t", operation="test"),
        )
    assert calls["count"] == 3  # 1 次原始 + 2 次重试
    assert len(sleeps) == 2 and all(s > 0 for s in sleeps)
```

- [ ] **1.2 跑测试确认失败**：`python -m uv run pytest tests/unit/infrastructure/test_llm_gateway.py -v` → 预期 FAIL（当前 401 会重试 4 次）

- [ ] **1.3 重构 gateway**：把 `OpenAICompatibleLLMGateway` 从 frozen dataclass 改为普通类，持有共享 client。替换 `_complete` 整段：

```python
RETRYABLE_STATUS = frozenset({408, 409, 429, 500, 502, 503, 504})


class OpenAICompatibleLLMGateway(LLMGateway):
    def __init__(self, *, base_url: str, api_key: str, default_model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._default_model = default_model
        self._client = httpx.AsyncClient(timeout=30.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _complete(
        self,
        *,
        operation: str,
        messages: list[dict[str, str]],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
        response_format: dict[str, str] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model_policy.model or self._default_model,
            "messages": messages,
            "temperature": 0.2,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-AgentMentor-Trace-Id": trace_context.trace_id,
        }
        url = f"{self._base_url}/chat/completions"
        last_error: Exception | None = None
        for attempt in range(model_policy.max_retries + 1):
            try:
                response = await self._client.post(url, headers=headers, json=payload)
                if response.status_code == 400 and "response_format" in payload:
                    # 兼容不支持 json_object 的 provider
                    payload.pop("response_format")
                    response = await self._client.post(url, headers=headers, json=payload)
                if response.status_code in RETRYABLE_STATUS or response.status_code >= 500:
                    response.raise_for_status()  # 转成异常进入下方分支
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise LLMGatewayError("LLM returned an empty message.")
                return content
            except httpx.HTTPStatusError as error:
                last_error = error
                status = error.response.status_code
                if status not in RETRYABLE_STATUS:
                    # 400/401/403 等：重试不可能成功，快速失败
                    raise LLMGatewayError(
                        f"LLM call failed with non-retryable status {status}: {error}"
                    ) from error
            except Exception as error:  # 网络错误/超时，可重试
                last_error = error
            if attempt < model_policy.max_retries:
                # 指数退避：1s, 2s, 4s...（cap 8s）
                await asyncio.sleep(min(8.0, 2.0**attempt))
        raise LLMGatewayError(f"LLM call failed after retries: {last_error}") from last_error
```

注意：文件顶部补 `import asyncio`；`generate_structured`/`stream_text`/`_messages`/`_extract_json` 保持不变（dataclass 改 class 后构造处无需变，`main.py:68` 用的是关键字参数）。

- [ ] **1.4 main.py 生命周期收尾**：`lifespan`（main.py:42-48）的 `yield` 后加：

```python
    llm = app.state.llm_gateway
    if isinstance(llm, OpenAICompatibleLLMGateway):
        await llm.aclose()
```

- [ ] **1.5 全量测试 + 提交**：`python -m uv run pytest` → 全绿后：

```bash
git add -A && git commit -m "refactor(llm): retryable-aware retry with backoff and shared AsyncClient"
```

### 验收标准

- `pytest` 全绿（基线数量不降）
- 单测证明：401 只调用 1 次；429 重试 3 次且有 sleep
- `grep -n "AsyncClient(" src/agent_mentor/infrastructure/llm.py` 只出现 1 次（`__init__` 里）

### 防坑清单

- frozen dataclass 改普通 class 后，如果 pyright 报 `LLMGateway` Protocol 不匹配（Protocol 是结构化的，方法签名对上即可），检查方法是否遗漏 `async`/参数名
- `monkeypatch.setattr("asyncio.sleep", ...)` 必须在模块 import 的 asyncio 上生效；如果 gateway 里写的是 `await asyncio.sleep(...)`，patch `asyncio.sleep` 即可
- 测试里 fake_post 的第一个参数是 `self`（patch 在类上）

---

## Day 2（3h）：真流式·网关层

### 现状与问题

`llm.py:61-79` 的 `stream_text`：先 `_complete` 拿全文，再 `content.split()` 逐词 yield——**伪流式**，首 token 延迟 = 全文生成时间。

### 设计决策（先给 ChatGPT 讲清楚）

真流式走 provider 的 `stream=True`。但注意：当前 RAG 回答用的是 `generate_structured`（JSON 含 citation_chunk_ids），**流式模式下拿不到结构化引用**。因此采用「文本流 + 引用后置」两段式：

1. 流式生成答案文本（真 delta）
2. 流结束后，用一次轻量 `generate_structured` 调用提取引用 chunk_ids

本日只做第 1 段的网关层。

### 任务步骤

- [ ] **2.1 写失败测试**（追加到 test_llm_gateway.py）：

```python
async def test_stream_complete_yields_real_deltas(monkeypatch):
    """stream_complete 应逐 chunk 转发 provider 的 SSE delta。"""
    gateway = make_gateway()
    deltas = ["你好", "，", "世界"]

    async def fake_stream(self, url, **kwargs):  # noqa: ANN001
        async def line_iter():
            for d in deltas:
                yield f'data: {{"choices": [{{"delta": {{"content": "{d}"}}}}]}}\n\n'.encode()
            yield b"data: [DONE]\n\n"

        return httpx.Response(200, content=line_iter(), request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "stream", fake_stream)
    chunks = [
        c async for c in gateway.stream_complete(
            operation="test",
            messages=[Message(role="user", content="hi")],
            model_policy=ModelPolicy(),
            trace_context=TraceContext(trace_id="t", operation="test"),
        )
    ]
    assert chunks == ["你好", "，", "世界"]
```

- [ ] **2.2 跑测试确认失败**（方法不存在）

- [ ] **2.3 实现 `stream_complete`**（加进 gateway 类，同时给 `ports/llm_gateway.py` 的 `LLMGateway` Protocol 加同签名方法）：

```python
    async def stream_complete(
        self,
        *,
        operation: str,
        messages: Sequence[Message],
        model_policy: ModelPolicy,
        trace_context: TraceContext,
    ) -> AsyncIterator[str]:
        """真流式：转发 provider 的 SSE token 流。不做重试（流中断由上层降级）。"""
        payload = {
            "model": model_policy.model or self._default_model,
            "messages": self._messages(messages),
            "temperature": 0.2,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "X-AgentMentor-Trace-Id": trace_context.trace_id,
        }
        async with self._client.stream(
            "POST", f"{self._base_url}/chat/completions", headers=headers, json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                chunk = json.loads(line[6:])
                delta = chunk["choices"][0]["delta"].get("content")
                if delta:
                    yield delta
```

注意：async generator 方法上不能用 `async def` + `return` 混用；`stream_text`（伪流旧方法）**保留不删**——测试的 FakeLLMGateway 和未迁移的调用点还在用。

- [ ] **2.4 Protocol 同步**：`ports/llm_gateway.py` 的 `LLMGateway` 加上 `stream_complete` 声明；检查 `tests/` 里所有 Fake/Stub LLM 实现是否需要补该方法（Protocol 若被显式继承会强制要求；仅鸭子类型则测试里用到再补）。

- [ ] **2.5 测试 + 提交**：

```bash
python -m uv run pytest && git add -A && git commit -m "feat(llm): real streaming via provider SSE passthrough"
```

### 验收标准

- 单测证明 delta 顺序转发、`[DONE]` 不产出、空 content 不产出
- 全量 pytest 绿

### 防坑清单

- httpx 的 `client.stream` 是 async context manager，测试里 mock 时返回的 Response 必须支持 `aiter_lines`（用 `content=` 传 async byte iterator）
- DeepSeek 偶尔在 delta 里发 `content: ""`，代码已用 `if delta` 过滤
- **流式不做重试**是有意设计：重放半截流会造成重复输出，中断应降级为错误事件，Day 3 处理

---

## Day 3（2h）：真流式·服务层

### 现状与问题

`answer_service.py:171-193` 的 `answer_events`：`await self.answer(...)` 拿到完整结果后 `result.answer.split()` 逐词 yield——用户看到的"流式"是假的，SSE 端点（api/chat.py:129）只是转发这些事件。

### 任务步骤

- [ ] **3.1 拆流式路径**：在 `AnswerService` 新增私有方法 `_stream_llm_answer`，把 `answer_events` 改为：

```python
    async def answer_events(self, **kwargs: object) -> AsyncIterator[dict[str, object]]:
        yield {"event": "retrieval.started", "data": {"question": kwargs.get("question")}}
        try:
            result = await self.answer(**kwargs)  # type: ignore[arg-type]
            yield {"event": "retrieval.completed", "data": {"candidate_count": len(result.candidates)}}
            if result.generation_mode == "llm" and self._llm is not None:
                # 真流式：重新走一次流式生成（引用与持久化沿用 result）
                prompt = self._build_answer_prompt(result)  # 见 3.2
                collected: list[str] = []
                async for delta in self._llm.stream_complete(
                    operation="rag_answer_stream",
                    messages=prompt,
                    model_policy=ModelPolicy(timeout_seconds=60.0),
                    trace_context=TraceContext(trace_id=str(result.message_id), operation="rag_answer_stream"),
                ):
                    collected.append(delta)
                    yield {"event": "answer.delta", "data": delta}
            else:
                for token in result.answer.split():
                    yield {"event": "answer.delta", "data": token}
            yield {"event": "answer.references", "data": [str(c.chunk_id) for c in result.citations]}
            yield {"event": "answer.completed", "data": {"message_id": str(result.message_id)}}
        except Exception as error:
            log_event(logging.WARNING, "rag_answer.stream_failed",
                      error_type=type(error).__name__, fallback="sse_error_event")
            yield {"event": "answer.failed", "data": {"error": str(error)}}
```

- [ ] **3.2 抽取 prompt 构造**：现有 `_generate_answer` 里拼 messages 的逻辑抽成 `_build_answer_prompt(...)`（供 `generate_structured` 和流式两路复用，参数按现有代码实际签名调整——**让 ChatGPT 读 answer_service.py 的 `_generate_answer` 后完成抽取，原则：非流式路径行为零变化**）。

- [ ] **3.3 补集成测试**：`tests/integration/` 里找现有 SSE/answer 测试，加一条：LLM 模式下 `answer.delta` 事件应大于 1 个且首个 delta 在 `retrieval.completed` 之后立即出现（用 FakeLLM 的 `stream_complete` yield 多段）。

- [ ] **3.4 手工验收 + 提交**：

```powershell
# 前端开流式提问，或 curl 观察事件间隔
curl -N -X POST http://localhost:8000/api/v1/knowledge-bases/<kb_id>/ask/stream -H "Content-Type: application/json" -d '{"question": "RAG 的作用是什么"}'
```

观察：`answer.delta` 应该**陆续**到达（肉眼可见间隔），而不是一坨齐发。

```bash
git add -A && git commit -m "feat(rag): true streaming answer via gateway stream_complete"
```

### 验收标准

- 非 LLM 降级路径（无 Key）行为不变，现有测试全绿
- LLM 路径 curl -N 可见 delta 陆续到达
- 已知取舍写进代码注释：流式生成的内容与落库的 `result.answer` 来自两次调用，可能轻微不一致（引用以落库为准）——面试可讲的 trade-off

### 防坑清单

- 两次调用的成本问题（一次结构化 + 一次流式）是本方案代价，V2 可改「流式 + 后置引用提取」单次调用，先记录到 TODO
- `kwargs.get("question")` 类型是 object，SSE 序列化没问题
- FakeLLMGateway 若被 Protocol 强制实现 `stream_complete`，最简单是 yield 整段文本一次

---

## Day 4（4h）：BGE·第一阶段（代码侧）

**深度参考**：`docs/operations/bge-embedding-migration-plan.md` 第 2~5 节（含完整代码）。本卡只做裁剪和验收，代码以该文档为准。

- [ ] **4.1** `pyproject.toml` 加 `sentence-transformers>=3.0,<4.0`（torch 由 uv 自动解析），`uv sync`
- [ ] **4.2** 新建 `src/agent_mentor/infrastructure/bge_embedding.py`（代码照抄迁移文档 3.1 节）
- [ ] **4.3** `config.py` 加 `embedding_provider: str = "bge"`，`embedding_model` 默认值改 `"BAAI/bge-small-zh-v1.5"`，`embedding_dimension` 改 `int | None = None`
- [ ] **4.4** `main.py` 按 provider 注入（照抄迁移文档 5.1 节）
- [ ] **4.5** 单测：`BgeEmbeddingGateway` 维度 == 512、同文本两次编码结果一致、batch 正常
- [ ] **4.6** **本日不切流量**：`.env` 保持 `AGENT_MENTOR_EMBEDDING_PROVIDER=development`，数据库不动
- [ ] 提交：`git commit -m "feat(embedding): BgeEmbeddingGateway with provider switch"`

**防坑**：
- 首次测试会下载 ~100MB 模型，家里网络慢就先手动下载到 HF 缓存
- **绝对不要在本日执行 alembic 迁移**——维度还是 1536，切了 provider 但不迁移，写入会报维度不匹配，这是预期内、留给 Day 5

---

## Day 5（3h）：BGE·第二阶段（数据侧）

**深度参考**：迁移文档第 6~10 节。

- [ ] **5.1** 备份数据库：`docker compose exec db pg_dump -U agentmentor agentmentor > backup_before_bge.sql`
- [ ] **5.2** 写 Alembic 迁移：chunks.embedding `Vector(1536)` → `Vector(512)`（**必须手动检查 autogenerate 结果**，pgvector 的 alter_column 需要 `postgresql_using`）
- [ ] **5.3** 新建 `scripts/reindex_embeddings.py`（照抄迁移文档 7.2 节）
- [ ] **5.4** 切换执行：`.env` 改 `AGENT_MENTOR_EMBEDDING_PROVIDER=bge` → `docker compose up -d --build` → `docker compose exec api alembic upgrade head` → `docker compose exec api python scripts/reindex_embeddings.py`
- [ ] **5.5** docker-compose.yml 加 `huggingface_cache` volume（迁移文档 8.2 节）
- [ ] **5.6** 端到端验证：上传一份新文档 + 用语义近义但**字面不同**的问题提问（例：文档讲"索引下推"，问"数据库怎么减少回表"），观察向量检索能命中
- [ ] 提交：`git commit -m "feat(embedding): switch to bge-small-zh with dimension migration and reindex"`

**防坑**：
- 迁移失败第一反应：`alembic downgrade -1` + 恢复备份，不要在半迁移状态调试
- reindex 脚本跑之前先 `select count(*) from chunks;` 记录总数，跑完对账
- 回滚三步：改 provider=development → downgrade → 重跑 reindex（用 Development gateway，需让脚本支持 provider 参数）

---

## Day 6（3h）：Eval Runner MVP

**深度参考**：`docs/operations/eval-runner-plan.md`。**裁剪原则：今天只做 retrieval 评估 + 报告落盘**，scoring_runner 留给下个迭代（评分 eval 依赖 LLM Key 且要改 EvaluationService，风险面大）。

- [ ] **6.1** 建 `evals/metrics.py`（只留 RetrievalMetrics + compute 函数，照抄该文档第 8 节 retrieval 部分）
- [ ] **6.2** 建 `evals/runners/retrieval_runner.py`（照抄第 5 节，删掉 answerable_accuracy 之外用不到的字段可后续补）
- [ ] **6.3** 建 `evals/run.py`：只支持 `--suite retrieval --knowledge-base-id <uuid>`，结果写 `evals/reports/retrieval-YYYYMMDD.json`
- [ ] **6.4** 准备 eval 知识库：用一个固定 KB，把 `evals/datasets/retrieval_v1.jsonl` 问题对应的源文档入库
- [ ] **6.5** 跑基线（此时已是 BGE）记下 recall@1/3/6；如果还想看对比，临时切回 development provider 重跑一次（成本 10 分钟，**这个对比数字是面试金句**）
- [ ] 提交：`git commit -m "feat(evals): retrieval eval runner with recall@k report"`

**防坑**：
- runner 里 `RetrievalQuery` 的 import 路径是 `agent_mentor.ports.knowledge_retriever`
- 无 LLM Key 也能跑 retrieval eval（只调 retriever），answerable_accuracy 那步如果依赖 AnswerService 可以先跳过

---

## Day 7（2h）：话术定稿 + 全量回归 + 收尾

- [ ] **7.1 全量回归**：`python -m uv run pytest` + `python -m uv run pyright` + 前端 `npm.cmd run build` 三绿
- [ ] **7.2 工作流话术（60 秒稿，背熟）**：

> "V1 的面试工作流我评估过 LangGraph。需求上只有 7 个线性节点、单用户、无并发分支，引入图引擎的运维复杂度大于收益，所以我用显式状态机 + PostgreSQL checkpoint 实现：每个节点转移落一条事件记录，进程重启后从 checkpoint 恢复，配合幂等键保证答案不重复提交。代价是条件路由要手写、没有可视化编排；如果节点数涨到 15+ 或需要人机协同分支，迁移路径是把状态机映射成 LangGraph 的 nodes/edges，checkpoint 结构已经是对齐的。"

- [ ] **7.3 更新三处面试材料**（在已有 interview 文档上改，不新建）：
  - "伪流式" → "SSE 真流式，网关层透传 provider delta"
  - "Feature Hashing" → "BGE-small-zh，带维度迁移和全量重嵌入的切换经历"（这是新弹药：切换过程本身就是好故事）
  - 补上 Day 6 的 recall 数字："BGE vs 哈希基线，recall@3 从 X 到 Y"
- [ ] **7.4 合并**：`hardening-v2` → `main`，打 tag `v0.2.0-hardening`
- [ ] **7.5 把结果同步回监工**：把 Day 6 报告数字 + 各日 commit hash 发回来，我做下一轮锐评

---

## 执行日志（每晚收工填写）

| 日期  | 任务 | 实际耗时 | 测试基线 | 遇到的问题 |
| ----- | ---- | -------- | -------- | ---------- |
| Day 1 |      |          |          |            |
| Day 2 |      |          |          |            |
| Day 3 |      |          |          |            |
| Day 4 |      |          |          |            |
| Day 5 |      |          |          |            |
| Day 6 |      |          |          |            |
| Day 7 |      |          |          |            |

**测试基线（开工前记录）**: ______ 通过
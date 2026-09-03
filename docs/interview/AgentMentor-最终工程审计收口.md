# AgentMentor 最终工程审计收口

> 目标：在不大改架构的前提下，对已经完成的 V2 工程做最后一轮“可面试、可解释、可回归”的质量收口。
>
> 审计日期：2026-09-03

## 1. 本轮为什么要审计

AgentMentor 已经具备完整闭环：资料入库、RAG 问答、模拟面试、逐题评分、报告历史、画像更新、复习推荐、知识库隔离、BGE 检索增强。

但从面试视角看，“功能跑通”还不够。面试官通常会继续追问：

- 接口异常时返回是否稳定？
- 状态机是否会出现重复提交、重复评分、脏画像？
- RAG 是否会编造引用？
- 检索到相似但不相关的片段时，系统是否会误答？
- 这些问题有没有自动化测试兜底？

所以本轮审计不追求继续加功能，而是把项目从“能演示”推进到“可验证、可解释、可回归”。

## 2. 审计范围

本轮聚焦三个 P1 方向：

1. API 契约与异常路径审计；
2. 数据一致性与状态机审计；
3. RAG 引用可信度审计。

这三个方向对应项目的三条核心防线：

```text
用户请求
  ↓
API 契约稳定性
  ↓
业务状态与数据一致性
  ↓
RAG / LLM 输出可信性
  ↓
画像与复习闭环
```

## 3. API 契约与异常路径审计

### 3.1 审计目标

接口层最怕的问题不是“正常路径能跑”，而是异常路径返回不一致。比如有的接口返回 `detail`，有的接口返回字符串，有的接口直接 500，这会让前端难以处理，也会削弱项目工程性。

本轮新增 API 契约测试，重点验证：

- 参数校验失败时，统一返回 `VALIDATION_ERROR`；
- 缺少 `Idempotency-Key` 时，返回稳定错误结构；
- 应用层抛出 `AppError` 时，接口层能转换为统一响应；
- RAG 问答接口返回字段稳定，包含证据充足性、生成模式、引用和检索解释；
- 评分报告接口即使没有逐题评分列表，也能返回稳定结构。

### 3.2 代码路线

| 关注点 | 代码位置 |
| --- | --- |
| FastAPI app 初始化 | `src/agent_mentor/main.py` |
| 统一异常处理 | `src/agent_mentor/api/errors.py` |
| 面试接口 | `src/agent_mentor/api/interviews.py` |
| RAG 问答接口 | `src/agent_mentor/api/chat.py` |
| 评分报告接口 | `src/agent_mentor/api/evaluations.py` |
| 新增契约测试 | `tests/api/test_contracts.py` |

### 3.3 新增测试

```text
tests/api/test_contracts.py
```

覆盖用例：

- `test_api_validation_errors_use_stable_error_contract`
- `test_submit_answer_requires_idempotency_key_header`
- `test_app_error_is_mapped_to_uniform_response_body`
- `test_ask_endpoint_preserves_grounded_answer_contract`
- `test_report_endpoint_allows_empty_evaluation_list_contract`

### 3.4 面试表达

可以这样讲：

> 我没有只验证 happy path，而是补了接口契约测试。因为前端工作台依赖稳定字段，比如错误码、trace_id、RAG 的 evidence_sufficient、generation_mode、citations。如果后端异常返回不稳定，前端状态恢复和错误提示会很脆弱。所以我把常见异常路径纳入了自动化回归。

## 4. 数据一致性与状态机审计

### 4.1 审计目标

AgentMentor 的核心不是一次性问答，而是一个长期训练闭环。因此数据一致性比普通 demo 更重要。

本轮重点确认：

- 同一场面试中题目序号不能重复；
- 同一道题的同一个幂等键不能重复提交；
- 同一个回答不能重复评分；
- 同一场面试只能有一份最终报告；
- 同一个 evaluation 只能触发一次画像更新事件；
- 题目引用、评分引用不能重复；
- 能力画像必须按知识库隔离，不能跨知识库污染。

### 4.2 代码路线

| 关注点 | 代码位置 |
| --- | --- |
| 面试状态与领域规则 | `src/agent_mentor/domain/interview.py` |
| 面试应用服务 | `src/agent_mentor/application/interview_service.py` |
| 评分应用服务 | `src/agent_mentor/application/evaluation_service.py` |
| 画像应用服务 | `src/agent_mentor/application/profile_service.py` |
| 数据模型与唯一约束 | `src/agent_mentor/infrastructure/database/models.py` |
| 状态机/一致性测试 | `tests/unit/test_data_consistency_constraints.py` |

### 4.3 新增测试

```text
tests/unit/test_data_consistency_constraints.py
```

覆盖用例：

- `test_interview_questions_are_unique_per_session_sequence`
- `test_user_answers_are_idempotent_per_question_key`
- `test_each_answer_can_have_only_one_evaluation`
- `test_each_interview_can_have_only_one_report`
- `test_profile_update_event_is_idempotent_per_evaluation`
- `test_question_and_evaluation_references_are_not_duplicated`
- `test_question_coverage_and_ability_profile_are_scoped_by_knowledge_base`

### 4.4 面试表达

可以这样讲：

> 这个项目里我把幂等和唯一性作为状态机的一部分处理。比如提交答案不仅前端防重复，数据库层也通过唯一约束兜底；评分和报告也不能重复生成污染画像。画像又按 knowledge_base_id 隔离，避免 Java 知识库和 Agent 知识库的能力数据混在一起。

## 5. RAG 引用可信度审计

### 5.1 审计目标

RAG 项目最容易被质疑的是“你到底有没有防幻觉”。因此本轮不是只看召回率，而是重点审计两件事：

1. 检索到的内容是否真的支持问题；
2. LLM 返回的引用是否真的来自本次检索上下文。

### 5.2 代码路线

| 关注点 | 代码位置 |
| --- | --- |
| RAG 问答编排 | `src/agent_mentor/application/answer_service.py` |
| 查询归一化、RRF、引用校验 | `src/agent_mentor/rag/retrieval.py` |
| 检索实现 | `src/agent_mentor/infrastructure/retriever.py` |
| LLM 网关端口 | `src/agent_mentor/ports/llm_gateway.py` |
| RAG 边界测试 | `tests/unit/test_retrieval.py` |
| LLM fallback 可观测性测试 | `tests/unit/test_llm_fallback_observability.py` |

### 5.3 新增/补强测试

本轮补强两个关键用例：

```text
tests/unit/test_retrieval.py
```

- `test_answer_service_assesses_only_lexically_supported_candidates`

验证点：

- 即使某个无关 chunk 分数很高，只要缺少词面支持，也不能被当成有效证据；
- 证据充足性只基于“支持问题的候选片段”判断，而不是盲目相信检索分。

```text
tests/unit/test_llm_fallback_observability.py
```

- `test_answer_service_downgrades_when_llm_hallucinates_citation`

验证点：

- 如果 LLM 返回了不在候选上下文里的 `chunk_id`，系统不会把它当作可信答案；
- 系统会降级到 deterministic grounded answer；
- 日志中保留 `rag_answer.llm_fallback`，便于定位模型输出问题。

### 5.4 面试表达

可以这样讲：

> 我没有把 RAG 的可信性交给模型自觉，而是在应用层做了两道门禁。第一道是证据门禁：检索候选必须和问题有词面支持，否则即使分数高也不能判定证据充足。第二道是引用白名单：LLM 只能引用本次检索返回的 chunk_id，不能编造引用。引用校验失败时不会污染结果，而是降级并记录日志。

## 6. 本轮验收结果

专项验收命令：

```powershell
.\.venv\Scripts\ruff.exe check tests/api/test_contracts.py tests/unit/test_data_consistency_constraints.py tests/unit/test_retrieval.py tests/unit/test_llm_fallback_observability.py
.\.venv\Scripts\pyright.exe tests/api/test_contracts.py tests/unit/test_data_consistency_constraints.py tests/unit/test_retrieval.py tests/unit/test_llm_fallback_observability.py
.\.venv\Scripts\pytest.exe tests/api/test_contracts.py tests/unit/test_data_consistency_constraints.py tests/unit/test_retrieval.py tests/unit/test_llm_fallback_observability.py -q
```

结果：

```text
ruff:   All checks passed
pyright: 0 errors, 0 warnings
pytest: 25 passed, 1 warning
```

说明：

- 1 个 warning 来自 FastAPI/TestClient 依赖链的 `httpx` 兼容提示，不是项目业务逻辑问题；
- 本轮没有修改业务架构，只补强了测试证据和审计文档；
- 新增测试覆盖 API 契约、数据一致性、RAG 可信边界三类高价值追问点。

## 7. 这轮审计带来的项目价值

### 7.1 从“功能堆叠”变成“工程闭环”

现在项目不是简单地把 RAG、LLM、画像、前端拼在一起，而是能说明：

- 输入错误如何处理；
- 状态重复如何防止；
- 评分和画像如何避免脏数据；
- RAG 如何控制幻觉；
- LLM 不可靠时如何降级。

### 7.2 面试中更容易讲出深度

面试官如果追问“你怎么保证系统可靠”，可以沿着这条线回答：

```text
接口契约稳定
  → 幂等和唯一约束兜底
  → 状态机控制流程推进
  → 可信评分才更新画像
  → RAG 引用白名单防止编造引用
  → Eval / 单测 / 集成测试持续回归
```

### 7.3 后续可以停止大开发，转向面试准备

本轮审计后，项目已经具备比较完整的简历项目表达基础。后续不建议继续无限加功能，更建议进入：

- 源码走读；
- 面试问答打磨；
- 项目演示脚本固化；
- 简历表述压缩；
- 企业级 RAG 拓展思路准备。

## 8. 仍然需要诚实说明的边界

这个项目不是企业级生产 RAG 平台，仍有边界需要诚实表达：

- 文档解析对复杂版式、扫描件、表格语义的支持有限；
- 检索评估数据集规模较小，还不是长期线上 A/B 数据；
- LLM 评分虽然有 rubric 和降级机制，但仍需要更大规模人工标注集校准；
- 当前主要服务本地单用户学习训练场景，多用户权限、审计、租户隔离不是 V2 目标；
- 真流式、异步任务队列、后台重索引调度等能力仍可作为后续演进方向。

面试时可以这样收束：

> 我会把它定义成一个面向个人学习训练的 RAG + Agent 工程化项目。它没有冒充企业级平台，但我在 V2 里补了知识库隔离、画像闭环、BGE 检索增强、评分区分度 Eval、API 契约、状态一致性和 RAG 引用可信度测试。也就是说，它的价值不只是 demo，而是展示了我如何把一个 AI 应用从原型推进到可验证的工程闭环。


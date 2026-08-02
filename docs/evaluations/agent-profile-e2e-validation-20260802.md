# AgentMentor 真实资料、多轮面试与能力画像端到端验收

> 验收日期：2026-08-02（Asia/Shanghai）  
> 验收方式：官方资料调研 + 真实 API + DeepSeek + PostgreSQL/pgvector + 前端只读检查  
> 验收对象：知识摄入、RAG、面试状态机、可信评分、两层画像、复习任务、报告与幂等  
> 结论：**核心训练闭环可用，但 RAG 证据门禁和前端初始化存在高优先级问题；当前适合项目演示和个人训练，不宜声称已达到稳定生产质量。**

---

## 1. 验收目标

本轮不使用仓库原有演示资料，而是从外部官方来源重新整理资料并创建新知识库，验证：

1. 文档能否从 pending 进入 ready；
2. RAG 能否回答域内问题并拒绝域外问题；
3. DeepSeek 是否真实参与出题和评分；
4. 低质量回答是否产生低分、错误模式和复习任务；
5. 连续高质量回答是否渐进提高画像；
6. 复习任务是否需要连续两次可信高分才完成；
7. 重复答题、重复报告和重复画像更新是否幂等；
8. checkpoint 轨迹和前端页面是否可用。

---

## 2. 资料来源与测试知识库

### 2.1 官方资料

- [Anthropic：Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic：Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [LangGraph 官方文档：Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Microsoft Learn：Build Advanced RAG Systems](https://learn.microsoft.com/en-us/azure/developer/ai/advanced-retrieval-augmented-generation)
- [Microsoft Learn：RAG and Generative AI in Azure AI Search](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview)

没有复制整篇网页，而是整理为三份可追溯学习笔记：

1. `01-agent-workflow-and-persistence.md`
2. `02-enterprise-rag-retrieval.md`
3. `03-agent-evaluation.md`

文件位置：

```text
docs/evaluations/fixtures/agent-profile-e2e-20260802/
```

### 2.2 知识库

```text
knowledge_base_id = cabdd7ba-61f2-48c1-80fa-f3e9cc36a501
```

说明：知识库中文名称在 PowerShell 请求中发生编码损失，数据库显示为问号；这是本轮测试客户端构造请求的问题，不能直接归因于 API。文档正文通过 multipart 上传后能够正常解析和用于检索。

---

## 3. 运行态与摄入结果

### 3.1 运行态

```text
/health/ready   → ok
/health/runtime → llm_enabled=true, llm_model=deepseek-chat
```

本轮出题、回答生成和评分使用真实 `deepseek-chat`，不是无 Key 的确定性基线。

Docker CLI 在当前 Codex 会话中无权访问 Windows named pipe，因此 `docker compose ps` 返回权限错误；已经运行的 HTTP 服务仍可正常使用。此项属于当前操作会话权限限制。

### 3.2 文档状态

| 文档 | 初始状态 | 最终状态 |
|---|---|---|
| Agent 工作流与持久化 | pending | ready |
| 企业 RAG 检索 | pending | ready |
| Agent 评测 | pending | ready |

结论：三份新资料均成功完成解析、分块、Embedding、全文索引和 pgvector 入库。

---

## 4. RAG 验收

### 4.1 测试问题

1. 为什么需要同时使用全文检索和向量检索，RRF 解决什么问题？
2. Checkpoint、幂等键和人工中断分别解决工作流中的什么问题？
3. 企业 RAG 为什么必须在召回阶段执行权限过滤？
4. 请根据知识库解释量子纠缠实验中的贝尔不等式。

### 4.2 实际结果

| 问题 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 全文 + 向量 + RRF | 有证据回答 | `evidence_guard`，无引用 | **失败：假阴性** |
| Checkpoint/幂等/中断 | 有证据回答 | `llm`，3 条引用 | 通过 |
| ACL 前置过滤 | 有证据回答 | `llm`，3 条引用 | 通过 |
| 量子纠缠 | 证据不足并拒答 | `llm`，3 条不相关引用 | **失败：假阳性** |

### 4.3 关键发现

当前证据充分性判断为：

```text
候选非空
+ Top1 RRF 分达到阈值
+ Query 与候选存在词法支持
```

该规则对知识边界的判断不够可靠：

- RRF 相关问题可能因为当前轻量 Embedding/词法判断没有形成足够支持而被拒答；
- 域外问题包含“资料、解释、实验”等普通词时，可能与无关片段产生词法交集，被错误放行；
- 引用白名单只能证明引用来自本轮候选，不能证明候选支持回答。

### 4.4 严重性

**P1，高优先级。**

这是项目“RAG 回答可验证”的核心卖点。当前白名单本身工作正常，但证据充分性和 claim-evidence 对齐不足。

### 4.5 建议

最小改动方向：

1. 为证据判断增加领域关键词覆盖率和无关主题检测；
2. 将词法支持从“任意共有词”调整为有意义术语覆盖；
3. 对每个回答 claim 增加引用片段支持检查；
4. 建立可回答/不可回答的固定评测集；
5. 生产阶段替换当前特征哈希 Embedding，并增加 reranker。

---

## 5. 三轮模拟面试设计

### 5.1 固定条件

```text
topic      = LangGraph checkpoint 与 Agent 工作流可靠性
difficulty = medium
每轮题数   = 1
```

选择单题是为了让“同主题、不同回答质量”之间的画像变化更容易观察。

### 5.2 回答策略

| 轮次 | 回答方式 | 目的 |
|---|---|---|
| 第 1 轮 | 故意回答“不知道” | 建立低分、错误和复习任务 |
| 第 2 轮 | 使用该题生成时的参考答案 | 验证第一次可信高分 |
| 第 3 轮 | 使用该题生成时的参考答案 | 验证第二次连续可信高分 |

限制说明：使用系统生成的参考答案验证的是**流程机械正确性**，不能证明评分具备独立客观性，因为出题参考答案和评分模型存在同源偏差。

---

## 6. 评分结果

| 轮次 | 总分 | 四维分 | 状态 | 置信度 | 复核 |
|---|---:|---|---|---:|---|
| 第 1 轮 | 0/20 | 0 / 0 / 0 / 0 | final | 0.95 | needs_review，已复核 |
| 第 2 轮 | 18/20 | 5 / 5 / 4 / 4 | final | 0.95 | 不需要复核 |
| 第 3 轮 | 20/20 | 5 / 5 / 5 / 5 | final | 1.00 | 不需要复核 |

结论：

- 评分能够区分明显无效回答和完整参考答案；
- 第 1 轮虽然置信度较高，但仍触发了复核流程；
- 总分由四维分确定，结果结构完整；
- 三轮都为 `final`，因此均允许进入画像。

尚未验证：

- `review_pending` 对画像的阻断；
- `disputed` 对画像的阻断；
- 低置信 final 的 0.5 权重路径；
- 人工评分与 LLM 评分的一致性。

这些路径已有单元测试，但本轮真实 DeepSeek 场景没有自然触发。

---

## 7. 两层能力画像结果

### 7.1 稳定主题与子知识点

本轮 Topic 被规范化为 `LangGraph`，动态知识点被规范化为：

- 状态建模；
- Checkpoint 与恢复；
- 图编排；
- 人工介入。

这证明自由文本主题没有直接生成四个无结构主画像，而是进入稳定 Topic 和 canonical subtopic。

### 7.2 掌握度变化

| 节点 | 第 1 轮 | 第 2 轮 | 第 3 轮 |
|---|---:|---:|---:|
| LangGraph 主题 | 0.4100 | 0.4982 | 0.5885 |
| 状态建模 | 0.4100 | 0.4982 | 0.5885 |
| Checkpoint 与恢复 | 0.4100 | 0.4982 | 0.5885 |
| 图编排 | 0.4100 | 0.4982 | 0.5885 |
| 人工介入 | 0.4100 | 0.4100 | 0.4100 |

结论：

- 画像没有把第 3 轮 100% 直接覆盖成 1.0，而是渐进提升到 0.5885；
- 主题和实际再次命中的子知识点共同更新；
- “人工介入”未被后两轮问题再次命中，因此没有随主题一起虚假提升；
- 两层画像的粒度控制符合设计预期。

---

## 8. 复习任务结果

### 8.1 第 1 轮低分后

| 子知识点 | 状态 | 优先级 | streak | 错误类型 |
|---|---|---:|---:|---|
| 状态建模 | open | 3 | 0 | concept_confusion |
| Checkpoint 与恢复 | open | 3 | 0 | concept_confusion |
| 图编排 | open | 3 | 0 | concept_confusion |
| 人工介入 | open | 3 | 0 | concept_confusion |

### 8.2 第 2 轮高分后

状态建模、Checkpoint 和图编排：

```text
status=open
priority=2
verification_streak=1
```

任务没有因一次高分直接完成，符合预期。

### 8.3 第 3 轮高分后

状态建模、Checkpoint 和图编排：

```text
status=completed
priority=1
verification_streak=2
```

“人工介入”仍然：

```text
status=open
priority=3
verification_streak=0
```

### 8.4 结论

**连续两次可信高分完成任务的机制通过真实端到端验证。**

系统按匹配到的子知识点推进任务，而不是只要 LangGraph 主题得高分就完成全部相关任务。这是两层画像模型最重要的有效性证据之一。

---

## 9. 幂等与一致性验证

### 9.1 重复答题

对第 3 轮使用相同 Idempotency-Key 重复提交：

```text
answer_count_before = 1
answer_count_after  = 1
interview_status    = completed
```

结果：通过。

### 9.2 重复生成报告

连续两次调用报告生成：

```text
report_id_first  = a2c4f8f6-35d8-4b73-9be0-24bbc293a144
report_id_second = a2c4f8f6-35d8-4b73-9be0-24bbc293a144
```

结果：报告 ID 稳定，通过。

### 9.3 重复画像更新

重复应用第 3 轮 Evaluation 后：

```text
LangGraph topic version        = 3 → 3
checkpoint subtopic version    = 3 → 3
orchestration subtopic version = 3 → 3
state subtopic version         = 3 → 3
```

结果：ProfileUpdateEvent 幂等门禁有效，通过。

---

## 10. 工作流轨迹

每轮单题面试记录了 5 个 checkpoint：

```text
load_profile
→ plan_interview
→ wait_for_answer
→ persist_answer
→ finish_interview
```

`wait_for_answer` 正确标记 `waiting_for_answer=true`，完成后进入 `finish_interview`。

### 发现的问题

工作流节点的 `label` 和 `output_summary` 从 API 返回时出现乱码。检查源码后，`src/agent_mentor/workflows/interview.py` 中的中文常量本身已经乱码，因此这不是单纯终端显示问题。

严重性：**P1（展示与可解释性）**。

建议：将该文件统一保存为 UTF-8，重写节点中文常量，并增加一个断言中文标签不包含替换字符或典型 mojibake 序列的测试。

---

## 11. 前端只读验收

### 11.1 API 代理

通过 `http://localhost:3000` 的代理直接访问：

```text
/api/v1/knowledge-bases → 返回 37 个知识库
/health/runtime         → llm_enabled=true, deepseek-chat
```

代理链路本身可用。

### 11.2 页面状态

页面初次加载及刷新后仍显示：

```text
本地降级模式
尚未创建知识库
可检索资料 0 份
当前面试未开始
演示就绪 0/0
```

同时知识库切换、新建和刷新按钮处于 disabled。

这与代理 API 返回的真实状态矛盾。

严重性：**P1（用户可用性）**。

可能方向：

- 前端初始化 Promise 中某个必需接口失败，导致全部状态没有落地；
- 运行中的前端 Bundle 与当前源码/API 契约不一致；
- 初始化错误被吞掉，没有显示错误消息；
- 前端默认 runtime 状态在请求失败后没有区分“未加载”和“本地降级”。

本轮只做验证，没有修改代码。修复时应先读取初始化请求的实际失败项，而不是在前端写死知识库数据。

---

## 12. 测试隔离限制

当前项目使用本机默认用户，画像和复习任务不按知识库隔离。本轮新知识库产生的 LangGraph 画像与历史项目数据共存：

```text
最终 abilities 总数    = 15
最终 review tasks 总数 = 16
```

因此本报告只比较本轮 `topic_key=langgraph` 的版本和子知识点，不能使用全局任务数量判断本轮新增数。

这符合当前“本机单用户”产品约束，但不利于自动化验收隔离。建议未来至少提供：

- 专用测试用户或 profile namespace；
- 按 test run 标记生成的数据；
- 可控的测试数据清理入口；
- 不影响真实画像的 dry-run 模式。

---

## 13. 测试过程产生的遗留数据

第一次自动化脚本错误地使用 `answer_text` 而非 API 契约要求的 `answer`，服务正确返回 422。由于初版脚本没有失败即停，产生了至少一场停留在 `waiting_for_answer` 的测试面试。

当前 API 没有删除或归档面试的端点，本轮没有越权直接删除数据库记录。该现象也说明系统需要：

- 客户端错误立即停止；
- 长时间 waiting 会话的归档策略；
- 测试数据标识和清理机制。

---

## 14. 总体验收矩阵

| 能力 | 结果 | 评价 |
|---|---|---|
| 官方资料整理与入库 | 通过 | 三文档全部 ready |
| 真实 DeepSeek 接入 | 通过 | 出题、回答、评分均启用 |
| 域内 RAG | 部分通过 | 2/3 域内问题成功 |
| 域外拒答 | 失败 | 量子纠缠问题被错误放行 |
| 引用白名单 | 通过但能力有限 | 引用合法，不代表语义支持 |
| 面试状态流 | 通过 | 单题三轮均完成，5 checkpoint |
| 低质量识别 | 通过 | 0/20 并生成错误任务 |
| 高质量识别 | 通过 | 18/20、20/20 |
| 两层画像渐进更新 | 通过 | 0.4100 → 0.4982 → 0.5885 |
| 子知识点独立更新 | 通过 | 未命中的人工介入保持不变 |
| 连续高分完成任务 | 通过 | streak 0 → 1 → 2/completed |
| 答题幂等 | 通过 | 重放后答案仍为 1 |
| 报告幂等 | 通过 | 重复构建 ID 稳定 |
| 画像幂等 | 通过 | 重复应用版本不变 |
| 工作流中文轨迹 | 失败 | 源码中文常量乱码 |
| 前端读取真实状态 | 失败 | UI 与可用代理 API 状态矛盾 |
| 测试数据隔离 | 受限 | 默认用户画像混合历史数据 |

---

## 15. 可用程度判断

### 可以确认

- 画像不是静态百分比，能够被真实评分渐进驱动；
- 错误、复习任务、连续验证和任务完成形成了真实闭环；
- 同主题下没有把所有子知识点一起虚假提升；
- 面试状态、答题、报告和画像更新具备基础幂等；
- DeepSeek 可以真实参与完整流程。

### 不能确认

- 当前 RAG 能稳定判断知识边界；
- 参考答案评分等同于真实用户能力评估；
- 多文档、大规模或复杂 PDF 的质量；
- 前端当前构建可以稳定加载运行数据；
- 企业多租户和隔离能力。

### 最终结论

> **能力画像和复习闭环的核心机制达到了可演示、可解释、可继续优化的程度；RAG 证据边界与前端初始化尚未达到“放心交给用户长期使用”的程度。**

建议先修复两个 P1：

1. RAG 域外问题假阳性/域内问题假阴性；
2. 前端初始化后错误显示“无知识库 + 本地降级”。

随后修复工作流中文常量乱码，并补充隔离式端到端测试。

---

## 16. 验收证据文件

```text
docs/evaluations/fixtures/agent-profile-e2e-20260802/
├── 01-agent-workflow-and-persistence.md
├── 02-enterprise-rag-retrieval.md
├── 03-agent-evaluation.md
├── 01-ingestion-result.json
├── 02-rag-results.json
├── round-1.json
├── round-2.json
├── round-3.json
├── 03-final-profile.json
└── 04-idempotency-results.json
```

JSON 文件包含本轮真实 API 结果。部分中文在 Windows PowerShell 5.1 的控制台展示中出现编码错位，UUID、状态、分数、置信度、版本和任务字段不受影响。


# AgentMentor 面试演示脚本

> 定位：这份文档用于你在面试前或面试现场演示项目。它不是技术设计文档，而是“打开项目之后怎么点、怎么讲、异常时怎么兜底”的操作台词。

## 1. 演示目标

演示时不要试图把所有功能都点一遍。你要让面试官看到三件事：

1. 资料可以进入知识库，并被 RAG 使用。
2. 面试题不是凭空生成，而是基于知识库和画像生成。
3. 回答之后会产生评分、报告、画像和复习计划，形成闭环。

一句话演示主线：

```text
上传资料 → RAG 验证 → 模拟面试 → 可信评分 → 能力画像 → 下一轮计划
```

## 2. 演示前准备

### 2.1 检查环境

在项目根目录执行：

```powershell
docker compose ps
```

理想状态：

```text
db        running
api       running
frontend  running
```

如果服务没有启动：

```powershell
docker compose up -d --build
```

### 2.2 检查接口健康

浏览器打开：

```text
http://localhost:3000/
```

也可以检查：

```text
http://localhost:8000/health/ready
http://localhost:8000/health/runtime
```

讲法：

> 项目是 Docker Compose 三容器部署，包含 PostgreSQL/pgvector、FastAPI 后端和 React 前端。这个约束是刻意设计的，目标是在 16GB 普通开发机上稳定演示。

### 2.3 检查 LLM 配置

如果前端运行状态显示 `LLM` 或 `deepseek-chat`，说明已接入真实模型。

如果显示本地 fallback，也不要慌，可以这样解释：

> 系统支持 OpenAI-compatible Gateway，DeepSeek 通过环境变量配置。为了保证无 Key 或接口失败时演示链路不中断，我保留了确定性 fallback。但正式演示时我会尽量使用真实 Key。

## 3. 推荐演示路线

### 3.1 第一幕：介绍项目

打开首页后，先不要急着点按钮，先讲 30 秒：

> 这个项目叫 AgentMentor，是我为了从 Java 后端转 AI Agent 开发做的个人学习训练系统。它不是普通聊天机器人，而是把学习资料入库、RAG 问答、模拟面试、可信评分、能力画像和复习计划串成一个闭环。我的目标是让 AI 不只是回答问题，还能持续评估我到底掌握了什么、哪里薄弱、下一轮该练什么。

如果面试官问“为什么不用 ChatGPT/Codex 直接问”，答：

> 通用工具可以辅助学习，但它不会天然维护我的知识库状态、面试记录、能力画像、复习任务和跨轮趋势。这个项目的价值在于把这些过程产品化和工程化。

## 4. 第二幕：知识库

### 4.1 操作

进入“知识库”区域。

推荐操作：

1. 选择已有的 `AI Agent 开发面试知识库`。
2. 点击刷新状态。
3. 展示已上传文档列表。

如果需要新增资料：

1. 点击上传学习资料。
2. 选择一份 Markdown / TXT / PDF / DOCX。
3. 等待状态变成 `ready`。

### 4.2 讲法

> 用户上传学习资料后，后端会做文档解析、分块、embedding 和入库。后续 RAG 问答和面试题生成都依赖这个知识库，所以题目和回答不是完全由模型自由发挥。

### 4.3 代码指路

```text
frontend/src/components/KnowledgePanel.jsx
frontend/src/components/KnowledgeBaseControls.jsx
src/agent_mentor/api/knowledge.py
src/agent_mentor/application/knowledge_service.py
src/agent_mentor/rag/documents.py
src/agent_mentor/rag/chunking.py
src/agent_mentor/infrastructure/embedding.py
```

### 4.4 注意事项

不要现场上传特别大的 PDF，避免等待时间不可控。面试演示优先使用已经准备好的知识库。

如果问“新建知识库但不上传资料会怎样”，答：

> V2 已经优化过交互，不会因为误点新建空知识库就找不到之前有资料的知识库。系统会尽量恢复最近有资料的知识库，避免用户状态丢失。

## 5. 第三幕：RAG 问答

### 5.1 操作

在 RAG 问答区域输入一个和资料相关的问题，例如：

```text
LangGraph 中 checkpoint 的作用是什么？它和普通缓存有什么区别？
```

或者：

```text
RAG 为什么需要引用溯源？证据不足时应该怎么处理？
```

### 5.2 讲法

> RAG 回答会先检索知识库片段，再把证据交给 LLM 生成回答。系统关注两个边界：一是回答要尽量带引用，二是证据不足时要显式降级，不能硬编。

### 5.3 代码指路

```text
frontend/src/components/RagPanel.jsx
src/agent_mentor/api/chat.py
src/agent_mentor/application/answer_service.py
src/agent_mentor/infrastructure/retriever.py
src/agent_mentor/rag/retrieval.py
src/agent_mentor/infrastructure/llm.py
```

### 5.4 可能追问

面试官问：“你怎么知道检索效果好不好？”

答：

> 我补了 eval runner，用固定数据集评估 Recall@1/3/6、MRR、证据充分率和不可回答拒答准确率。BGE 切换、chunk 策略或检索参数调整后，都可以用这个 runner 做对比，而不是只凭主观体验判断。

代码：

```text
evals/run.py
evals/metrics.py
evals/runners/retrieval_runner.py
```

## 6. 第四幕：模拟面试

### 6.1 操作

进入“模拟面试”区域。

推荐操作：

1. 输入或选择一个主题，例如：

```text
RAG 检索增强生成
```

2. 点击启动三题面试。
3. 第一题可以手动输入回答。
4. 如果现场时间紧，后续题可以点击“使用参考答案”。

### 6.2 讲法

> 面试流程不是一次性脚本，而是一个可恢复状态机。每一题生成后进入等待回答，用户提交后会持久化答案，再决定进入下一题还是完成面试。这里还加了 Idempotency-Key，避免重复点击导致同一题重复提交。

### 6.3 代码指路

```text
frontend/src/components/InterviewPanel.jsx
src/agent_mentor/api/interviews.py
src/agent_mentor/application/interview_service.py
src/agent_mentor/workflows/interview.py
src/agent_mentor/domain/interview.py
```

### 6.4 演示重点

你要重点讲两个点：

1. 题目基于知识库检索片段生成。
2. 题目会受到画像和覆盖盲区影响。

可以这样说：

> 原来系统更偏向根据低分项补缺，后来我发现还有一个问题：未考过的知识点并不等于掌握。所以 V2 增加了覆盖保底出题，三题面试中会留一题优先覆盖未验证知识点，让系统具备查漏能力。

代码：

```text
src/agent_mentor/application/interview_service.py
tests/unit/test_interview_service.py
```

## 7. 第五幕：评分报告

### 7.1 操作

完成三题后，点击生成评分或查看报告。

重点展示：

- 总分。
- 每题得分。
- 逐题解析。
- 扣分原因。
- 改进建议。

### 7.2 讲法

> 评分不是只展示一个大模型给出的总分，而是围绕 Rubric 生成结构化评价。前端会折叠展示逐题解析，避免内容太多影响阅读。最终报告既能看总览，也能展开看每题为什么扣分。

### 7.3 代码指路

```text
frontend/src/components/EvaluationPanel.jsx
frontend/src/components/ReportsPanel.jsx
src/agent_mentor/api/evaluations.py
src/agent_mentor/application/evaluation_service.py
src/agent_mentor/domain/evaluation.py
```

### 7.4 可能追问

面试官问：“为什么不能直接相信 LLM 总分？”

答：

> 因为 LLM 评分本身有波动，所以应用层要做结构化约束，包括 Rubric、引用白名单、置信状态和最终分计算。画像更新也不会消费所有评分，低置信或争议结果要降权或不更新。

## 8. 第六幕：能力画像与复习计划

### 8.1 操作

切到能力画像和下一轮计划区域。

重点展示：

- 当前知识库下的主画像。
- 需要加强的主题。
- 高频错误。
- 推荐下一轮题目。
- 报告历史和趋势。

### 8.2 讲法

> 画像不是把最近一次分数直接覆盖成百分比，而是做渐进更新。主画像是稳定主题，动态子知识点作为诊断证据。这样可以避免一次高分或一次低分让画像剧烈波动。

### 8.3 代码指路

```text
frontend/src/components/ProfilePanel.jsx
frontend/src/components/PlanPanel.jsx
frontend/src/components/TrendPanel.jsx
src/agent_mentor/api/profiles.py
src/agent_mentor/application/profile_service.py
src/agent_mentor/domain/profile.py
src/agent_mentor/domain/profile_taxonomy.py
```

### 8.4 可能追问

面试官问：“为什么我刚考了 55/60，画像还是 44？”

答：

> 画像不是最近一次分数，而是长期掌握度估计。它会结合可信评分、历史表现、复习任务状态和知识库维度渐进更新。这样可以防止一次高分直接掩盖长期薄弱点。不过连续高分会逐步提升画像，并解决相关复习任务。

## 9. 第七幕：报告历史与趋势

### 9.1 操作

展示报告历史区域。

重点说明：

- 多轮面试记录会沉淀。
- 可以看最近几轮分数变化。
- 可以用于观察训练是否有效。

### 9.2 讲法

> 这个功能是为了证明系统不是一次性问答，而是长期训练工具。用户可以通过历史报告看到自己在不同主题上的变化，也能反过来验证画像和复习计划是否合理。

### 9.3 代码指路

```text
frontend/src/components/ReportsPanel.jsx
frontend/src/components/TrendPanel.jsx
src/agent_mentor/api/evaluations.py
src/agent_mentor/application/evaluation_service.py
```

## 10. 演示中的推荐问题

### 10.1 RAG 问答推荐问题

```text
RAG 的核心流程是什么？为什么需要引用溯源？
```

```text
LangGraph 的 checkpoint 解决了什么问题？
```

```text
Agent Memory 和普通数据库记录有什么区别？
```

### 10.2 模拟面试推荐主题

```text
RAG 检索增强生成
```

```text
LangGraph 状态管理
```

```text
Agent Memory
```

```text
评估与可靠性
```

## 11. 演示异常兜底话术

### 11.1 如果 LLM 调用失败

话术：

> 当前外部模型接口可能受网络或 Key 影响。系统设计了 fallback，是为了保证本地演示链路不中断。但我不会把 fallback 效果当成真实模型效果，正式效果应以 DeepSeek/OpenAI-compatible 服务返回为准。

### 11.2 如果回答看起来不够好

话术：

> 这正是 RAG 系统需要评测的原因。V2 我补了检索评估入口，后续会用固定数据集比较 chunk、embedding 和检索参数，而不是只凭一次主观体验判断。

### 11.3 如果题目相似

话术：

> 早期确实出现过题目重复或集中在某个主题的问题，所以 V2 做了跨轮题目去重、画像驱动推荐和覆盖保底出题。现在的目标是既补低分，也覆盖未验证知识点。

### 11.4 如果画像变化慢

话术：

> 这是有意设计。画像是长期能力估计，不是最近一次面试分数。它应该稳定、渐进、可解释；否则一次异常评分就会污染长期画像。

### 11.5 如果被问为什么选择 BGE

话术：

> 早期版本用 development feature hash 是为了先跑通闭环，但它不是真正语义 embedding。当前版本已经采用重建式方案切到 BGE-small-zh：把 pgvector 维度调整为 512，清空旧历史向量，重新导入资料生成 embedding。这样比在线迁移简单，也符合个人学习项目“历史数据可重建”的约束。为了演示稳定性，代码里仍保留 development provider 作为无模型环境 fallback。

## 12. 10 分钟完整演示脚本

### 第 0 到 1 分钟：项目介绍

说：

> AgentMentor 是我做的一个 AI 面试训练助手，用来辅助我从 Java 后端转向 AI Agent 开发。它把资料入库、RAG 问答、模拟面试、可信评分、能力画像和复习计划串成一个闭环。

### 第 1 到 2 分钟：知识库

操作：

- 打开知识库区域。
- 选择已有 AI Agent 知识库。
- 展示资料列表。

说：

> 这里是知识库入口，上传的学习资料会被解析、切分、向量化并写入 pgvector。

### 第 2 到 3 分钟：RAG

操作：

- 输入一个 RAG 或 LangGraph 问题。
- 展示回答和引用。

说：

> 回答不是直接问模型，而是先检索证据，再生成带引用的回答。证据不足时要降级。

### 第 3 到 6 分钟：模拟面试

操作：

- 输入主题。
- 启动三题面试。
- 回答一题，另外两题可用参考答案。

说：

> 面试是可恢复状态机，每题有生成、等待回答、持久化、推进状态。提交时有幂等键，避免重复点击写入重复答案。

### 第 6 到 8 分钟：评分报告

操作：

- 展示总分。
- 展开一题解析。

说：

> 评分围绕 Rubric 和引用证据生成，报告里会解释扣分原因和改进方向。

### 第 8 到 9 分钟：画像和复习计划

操作：

- 展示能力画像。
- 展示下一轮计划。

说：

> 画像是长期能力估计，不是单次分数。系统会根据可信评分渐进更新，并生成复习任务。

### 第 9 到 10 分钟：总结亮点

说：

> 这个项目最核心的是把 RAG、LLM 评分、可恢复工作流、能力画像和复习计划串成闭环。它不是企业级平台，但已经覆盖了企业级 RAG/Agent 系统里几个关键工程问题：知识边界、状态一致性、结果可信、评测和本地部署成本控制。

## 13. 面试前自检清单

### 13.1 功能自检

- [ ] Docker 服务可以启动。
- [ ] 前端可以打开。
- [ ] 当前知识库可以恢复。
- [ ] RAG 问答可以返回。
- [ ] 三题面试可以完整完成。
- [ ] 报告可以生成。
- [ ] 画像和复习计划可以展示。
- [ ] 刷新页面后状态不丢。

### 13.2 表达自检

- [ ] 能用 1 分钟讲清项目背景。
- [ ] 能讲清 RAG 和普通聊天的区别。
- [ ] 能讲清面试状态机。
- [ ] 能讲清为什么评分不能直接污染画像。
- [ ] 能讲清为什么画像变化是渐进的。
- [ ] 能讲清为什么用重建式方案切换 BGE。
- [ ] 能讲清企业级 RAG 还缺哪些能力。

### 13.3 风险自检

- [ ] 不夸大成企业级 RAG。
- [ ] 不说完整接入 LangGraph。
- [ ] 不把 BGE 说成企业级向量服务，只说当前本地 BGE-small-zh 已落地。
- [ ] 不说复杂文档治理已经完全解决。
- [ ] 不把 fallback 结果当成真实大模型效果。

## 14. 最后一版口径

如果面试最后让你总结，你可以这样说：

> 我这个项目的价值不在于单点调用大模型，而在于把学习训练做成了一个可验证闭环。资料进入知识库后，RAG 负责知识边界，模拟面试负责主动验证，可信评分负责结构化反馈，能力画像负责长期记忆，复习计划负责下一轮行动。V2 里我又补了知识库隔离、画像渐进更新、覆盖保底出题和检索评估入口，让它更接近一个可持续迭代的 Agent 学习系统。

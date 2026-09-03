# AgentMentor V2 阶段性交接与代码走读文档

> 交接目标：让没有参与 V2 开发的同事，在 60～90 分钟内理解 V2 相比 V1 的增量、当前真实实现边界、核心业务流程、代码走读路线、运行方式和质量门禁。
>
> 本文以当前代码为事实来源。Phase 7～Phase 12 文档用于说明演进过程，不能替代源码。V1 文档继续独立保留，不在本文中覆盖。

## 1. 项目一句话

AgentMentor 是一个面向“Java 后端开发者转型 AI Agent 开发”的本地个人 AI 面试学习助手：用户把学习资料维护在知识库中，通过可溯源 RAG 验证知识，再完成画像驱动的模拟面试；系统对回答进行可信评分，沉淀报告历史、两层能力画像、错误模式和复习任务，并据此安排下一轮训练。

V2 的核心闭环：

```text
选择知识库
→ 上传与解析学习资料
→ 结构化分块和索引
→ 检索与 RAG 验证
→ 画像/复习任务驱动出题
→ 可恢复模拟面试
→ Rubric 可信评分
→ 报告历史与趋势
→ 稳定主题 + 动态子知识点画像
→ 复习任务验证
→ 下一轮专项训练
```

## 2. 项目背景与 V2 定位

V1 解决的是“学习资料 → RAG → 面试 → 评分 → 画像”能否在 16GB 普通开发机上完整跑通。V2 不再以增加按钮为目标，而是解决闭环长期使用时出现的工程问题：

1. 前端单页承载内容过多，功能虽全但难维护、难演示。
2. 画像已经存在，但没有充分反哺出题和专项训练。
3. 单轮报告不能体现长期学习效果。
4. 简单文档 RAG 难以回答企业场景中的结构、表格、代码块和召回解释问题。
5. 面试流程虽然有 checkpoint，但节点、事件和恢复路径不够显式。
6. 大模型生成的知识点措辞不稳定，导致高分后原画像不变化。
7. 创建、切换知识库和恢复面试的前端交互需要更可靠的状态隔离。

因此，V2 的定位是：

- 单用户、本地长期学习助手，不做多租户招聘平台。
- 画像和复习任务真正参与下一轮训练。
- 评分、画像、报告和工作流都具备可解释、幂等或防污染设计。
- 复杂文档能力采用轻量增强，明确企业级能力边界。
- 继续使用 Docker Compose 三服务，保持 16GB 开发机可运行。
- 不为了技术栈丰富而引入 Redis、Kafka、Elasticsearch、Kubernetes。

## 3. V1 到 V2 的能力变化

| 能力 | V1 | 当前 V2 |
| --- | --- | --- |
| 前端形态 | 单页功能演示 | 组件化任务工作台和分区导航 |
| 运行态 | 基础 health | LLM、RAG、fallback、评分和演示就绪度 |
| 训练主题 | 用户输入为主 | 画像、错误、复习任务和用户主题共同决定 |
| 出题 | 主题 + 检索片段 | 加入题型角度、近期题目去重和出题原因 |
| 报告 | 当前面试报告 | 报告历史、总分和四维趋势 |
| 文档解析 | Markdown/TXT/PDF/DOCX | 增加 block type、结构保留和检索解释 |
| Embedding | 确定性随机基线 | feature hashing 轻量相似度基线 |
| 工作流 | checkpoint 记录 | 显式节点规格、统一事件、轨迹接口和恢复 |
| 画像主键 | LLM 动态知识点文本 | 稳定主题 + 动态诊断子知识点 |
| 复习任务 | 创建、排序、手工完成 | 连续两次可信高分可自动解决 |
| 知识库交互 | 自动恢复一个当前库 | 选择、新建、切换，多知识库状态隔离 |
| 项目自检 | 手工判断 | `/api/v1/demo/readiness` 只读自检 |

## 4. V2 阶段范围

### 4.1 Phase 7：前端组件化与运行态观测

已完成：

- 知识库、RAG、面试、报告、画像、训练计划和系统状态拆为独立组件。
- API 请求统一通过 `frontend/src/api/client.js`。
- 报告与画像展示规则下沉到 `frontend/src/utils/`。
- 页面展示 LLM 模式、模型名称、RAG 证据状态、fallback 和评分状态。
- 后续继续重构为侧边栏导航和任务型工作台。

代码入口：

```text
frontend/src/main.jsx
→ frontend/src/components/AppLayout.jsx
→ frontend/src/components/*Panel.jsx
→ frontend/src/api/client.js
→ frontend/src/utils/*.js
```

### 4.2 Phase 8：画像驱动出题与专项训练

已完成：

- 从能力画像和待复习任务生成训练重点。
- 可从训练重点选择专项主题。
- 前端把选中的训练重点填充为面试主题，再由后端按该主题检索和出题。
- 同轮题目使用不同题型角度，近期题目参与去重。
- 画像为空时继续按用户主题和资料降级出题。

当前边界：

- 后端 `InterviewService` 尚未直接查询完整画像；画像对出题的影响通过“训练重点 → 面试主题”实现。
- 训练重点的 `reason` 会在前端展示，但尚未持久化为每道题的结构化 `why_this_question`。
- 去重主要覆盖同一轮历史题目，尚未实现跨多轮相似度索引。

代码入口：

```text
frontend/src/components/TrainingFocusPanel.jsx
→ frontend/src/main.jsx::selectTrainingFocus
→ src/agent_mentor/api/profiles.py
→ src/agent_mentor/application/profile_service.py
→ src/agent_mentor/api/interviews.py
→ src/agent_mentor/application/interview_service.py
```

### 4.3 Phase 9：报告历史与多轮趋势

已完成：

- 报告历史查询。
- 总分及四维评分趋势。
- 点击历史记录恢复报告详情。
- 逐题答案、得分、扣分原因和建议使用折叠结构展示。

代码入口：

```text
frontend/src/components/ReportHistoryPanel.jsx
→ src/agent_mentor/api/evaluations.py
→ src/agent_mentor/application/evaluation_service.py
→ InterviewReportModel / EvaluationModel
```

### 4.4 Phase 10：复杂文档 RAG 轻量增强

已完成：

- 识别 paragraph、heading、list、code、table、unknown。
- 分块时保留 heading path、页码、chunk index 等线索。
- 代码块保留换行，避免被普通文本归一化破坏。
- 检索结果暴露向量排名、全文排名、RRF 和检索解释。
- RAG 页面展示引用来源和召回原因。

当前边界：

- 数据库暂未单独持久化所有 block type，部分结果在检索层兼容推断。
- 不支持扫描 PDF OCR、复杂表格行列还原、公式和图片多模态理解。
- 不做版面坐标级引用。

代码入口：

```text
src/agent_mentor/rag/documents.py
→ src/agent_mentor/rag/chunking.py
→ src/agent_mentor/application/knowledge_service.py
→ src/agent_mentor/infrastructure/retriever.py
→ src/agent_mentor/application/answer_service.py
→ frontend/src/components/RagPanel.jsx
```

### 4.5 Phase 11：Agent 工作流显式化与中断恢复

已完成：

- 面试节点名称、事件名称、职责和 checkpoint 摘要统一定义。
- REST 接口返回工作流轨迹。
- SSE 暴露关键 workflow event。
- 页面刷新后恢复面试、当前题、答案和 checkpoint 轨迹。
- 生成题目、重复提交、评分和画像更新都有降级或保护策略。

必须准确理解当前边界：

- `InterviewService` 仍是业务编排中心。
- `workflows/interview.py` 提供显式节点语义和状态转换函数。
- `load_profile` 当前是工作流语义/checkpoint 节点，不在该函数中执行数据库画像查询；训练主题已由前端训练焦点选择提前确定。
- 当前没有引入 LangGraph 等重型运行时，不能描述为“完全由 LangGraph 执行的工作流”。

### 4.6 Phase 12：演示就绪度与项目自检

已完成：

- 检查知识库、READY 文档、checkpoint、已完成面试、报告和画像。
- 返回就绪分、状态、逐项检查和下一步建议。
- 自检只读，不写业务数据。

代码入口：

```text
frontend/src/components/RuntimeInsights.jsx
→ src/agent_mentor/api/demo.py
→ src/agent_mentor/application/demo_readiness_service.py
→ 已有业务表只读聚合
```

### 4.7 V2 收口后的稳定性增强

V2 Phase 完成后继续进行了不改变主架构的稳定性优化：

- RAG 响应明确 `generation_mode`、`model_name`、`fallback_reason`。
- 非核心前端接口失败不再拖垮整个工作台。
- 答案幂等键由前端按“面试 + 题目”保存并在成功后清理，数据库唯一约束落在“题目 + 幂等键”。
- 报告改为事务内创建或更新，避免失败时旧报告丢失。
- 启动时识别长时间 pending/processing 的文档。
- 重新索引按 `chunk_index` 原位更新，尽量保留 chunk ID 和历史引用。
- feature hashing 替代不保留相似性的 SHA256 随机向量。
- 历史题目参与题目生成去重。

### 4.8 两层能力画像增强

V2 最重要的收口改造之一：

- 稳定主题作为主画像，例如 RAG、LangGraph。
- 动态子知识点作为诊断证据，例如“检索与召回”“证据引用”。
- `disputed`、`review_pending` 不更新画像。
- 低置信 final 降权更新。
- 同一复习主题连续两次可信高分后自动完成任务。
- 旧画像保留为 legacy，新口径通过数据库迁移平滑加入。
- 启动时幂等回放历史评分，重复启动不会重复加分。

## 5. V2 总体架构

### 5.1 图片生成位置

> ![image-20260729225528381](project-handoff-v2.assets/image-20260729225528381.png)

图片生成规格：

- 风格参考 V1 总体架构图，使用中文节点、浅色背景、分层卡片和清晰箭头。
- 从上到下分为：交互层、接口层、应用服务层、领域/工作流/RAG 层、基础设施层、部署层。
- 交互层包含 React 工作台、知识库选择、RAG、面试、报告、画像、系统状态。
- 接口层包含 knowledge、chat、interviews、evaluations、profiles、demo、health。
- 应用层包含 KnowledgeService、AnswerService、InterviewService、EvaluationService、ProfileService、DemoReadinessService。
- 领域层包含 interview、evaluation、profile、profile_taxonomy、workflow node specs。
- RAG 层包含 DocumentParser、Chunking、Retriever、Embedding Gateway、LLM Gateway。
- 基础设施层包含 PostgreSQL、pgvector、HTTP Client 和本地文件卷。
- 部署层包含 Docker Compose 的 db、api、frontend 三容器，并标注“16GB 本地开发机约束”。
- 大模型服务画为外部依赖，标注 DeepSeek/OpenAI-compatible，无 Key 或失败时进入确定性 fallback。

### 5.2 纯文字架构说明

```text
React 工作台
    ↓ HTTP / SSE
FastAPI API
    ↓ 参数校验与协议转换
Application Service
    ├── 知识入库编排
    ├── RAG 回答编排
    ├── 面试工作流编排
    ├── 评分与报告编排
    ├── 两层画像与复习任务
    └── 演示就绪度聚合
    ↓
Domain / Workflow / RAG Ports
    ↓
PostgreSQL + pgvector + 文件存储 + 外部 LLM
```

依赖关系的核心约束：

- API 层不承载长期业务规则。
- Application Service 负责编排事务和端口调用。
- Domain 层保存评分、画像、状态迁移等纯规则。
- Infrastructure 层实现数据库、检索、Embedding 和 LLM 访问。
- 前端不计算唯一业务真相，只负责交互、状态恢复和结果展示。

## 6. 学习训练核心闭环

### 6.1 图片生成位置

> ![image-20260729231943934](project-handoff-v2.assets/image-20260729231943934.png)

图片生成规格：

- 使用顺时针闭环或上下两行闭环布局。
- 主链路节点：
  1. 选择知识库；
  2. 上传学习资料；
  3. 解析与结构化分块；
  4. PostgreSQL/pgvector 索引；
  5. 检索召回；
  6A. RAG 问答验证；
  6B. 画像驱动出题；
  7. 用户回答；
  8. 可信评分；
  9. 报告历史与趋势；
  10. 两层能力画像；
  11. 复习任务与下一轮专项训练。
- 从“复习任务与下一轮专项训练”使用虚线箭头返回“画像驱动出题”。
- 在“检索召回”处分为 RAG 问答和面试题生成两条消费路径。
- 在“可信评分”旁标注 disputed/review_pending 不污染画像。

### 6.2 流程和代码路线

#### A. 知识资料入库

```text
KnowledgePanel 上传文件
→ main.jsx::uploadDocument
→ POST /api/v1/knowledge-bases/{id}/documents
→ api/knowledge.py::upload_document
→ KnowledgeService.add_document
→ BackgroundTasks
→ KnowledgeService.ingest
→ DocumentParser
→ chunk_sections
→ EmbeddingGateway.embed
→ KnowledgeChunkModel / pgvector
```

走读重点：

- `KnowledgeService` 如何处理重复文件、状态更新和失败原因。
- `documents.py` 如何把不同格式统一成 section。
- `chunking.py` 如何保留 heading path、page number 和 block type。
- 为什么上传接口先返回 202，再由前端轮询状态。

#### B. RAG 问答验证

```text
RagPanel 提交问题
→ POST /api/v1/knowledge-bases/{id}/ask
→ api/chat.py
→ AnswerService.answer
→ PostgresHybridRetriever.retrieve
→ 全文检索 + pgvector 检索
→ reciprocal_rank_fusion
→ 证据阈值判断
→ LLM Gateway 或确定性降级
→ validate_citations
→ 答案 + 引用 + generation_mode
```

走读重点：

- `retriever.py` 如何组合全文和向量信号。
- `retrieval.py` 如何完成查询规范化、RRF 和引用白名单校验。
- `AnswerService` 如何区分证据充足、LLM 成功、模型失败和证据保护降级。

#### C. 模拟面试和评分

```text
TrainingFocusPanel / InterviewPanel
→ 创建面试
→ InterviewService.start
→ 加载画像和规划面试
→ 检索证据
→ 生成题目、参考答案和 Rubric
→ 等待用户回答
→ Idempotency-Key 保存答案
→ 推进下一题或完成面试
→ EvaluationService
→ 四维评分和复核路由
→ InterviewReportModel
→ ProfileService
```

#### D. 画像反哺下一轮

```text
EvaluationModel
→ ProfileService.apply_interview_evaluations
→ profile_update_decision
→ canonical_topic
→ canonical_subtopics
→ updated_mastery
→ ErrorPatternModel
→ ReviewTaskModel
→ recommend_interview_plan / training_focuses
→ 前端专项训练
```

## 7. 面试 Agent 工作流

### 7.1 图片生成位置

> ![image-20260730000715194](project-handoff-v2.assets/image-20260730000715194.png)

图片生成规格：

- 主状态从 Created 开始，依次经过加载画像语义节点、规划面试、生成题目、等待回答、保存答案。
- 保存答案后分支：
  - 未到最后一题：推进下一题并回到生成题目；
  - 最后一题：完成面试。
- 完成面试后由前端触发评分、报告和画像更新。
- 每个关键节点旁标注写入 WorkflowCheckpointModel。
- `WaitingForAnswer` 使用明显的“暂停/可恢复”视觉表达。
- `PersistAnswer` 旁标注 Idempotency-Key。
- 画像更新旁标注 disputed/review_pending 不更新、低置信 final 降权。
- 在 `load_profile` 旁标注“当前为语义/checkpoint 节点；训练主题由前端画像焦点提前注入”，避免图片夸大实现。

### 7.2 当前真实状态流转

```text
Created
→ load_profile（记录画像加载语义，当前不直接查询画像表）
→ plan_interview
→ generate_question
→ wait_for_answer
→ persist_answer
→ advance_question ──→ generate_question
→ finish_interview
→ Completed
→ 前端触发 Evaluation / Report / Profile Update
```

### 7.3 代码路线

```text
api/interviews.py
→ InterviewService.create_interview
→ InterviewService.start
→ workflows/interview.py
→ WorkflowCheckpointModel
→ InterviewService.submit_answer
→ domain/interview.py::assert_transition
→ GET /workflow-trace 或 SSE /events
→ frontend/src/components/InterviewPanel.jsx
```

走读顺序：

1. 先读 `domain/interview.py`，理解状态和合法迁移。
2. 再读 `workflows/interview.py`，理解节点名称、事件和 state 变化。
3. 再读 `InterviewService`，理解实际编排、数据库写入和降级。
4. 最后读 `api/interviews.py` 和 `InterviewPanel.jsx`，理解协议和展示。

不要把 `load_profile()` 理解为画像 Repository 调用。它当前只返回一个切换到
`load_profile` 节点的新状态并写入 checkpoint；真正的训练焦点来自前端调用
`/profiles/me/training-focuses` 后填入面试主题。

## 8. 两层能力画像与复习任务

### 8.1 图片生成位置

> ![image-20260730003356006](project-handoff-v2.assets/image-20260730003356006.png)

图片生成规格：

- 左侧输入：Interview Topic、Question required points、Evaluation。
- 中间第一层：稳定主题画像，例如 RAG、LangGraph、Agent 工具调用。
- 中间第二层：主题下的动态诊断子知识点。
- 右侧输出：错误模式、复习任务、训练重点、下一轮面试主题。
- 高分路径标注：可信高分第一次 `verification_streak=1`，第二次任务 completed。
- 低分路径标注：记录错误、重置 streak、提高或重算优先级。
- disputed/review_pending 使用阻断符号，表示不进入画像更新。
- legacy 历史数据使用灰色区域，箭头经过“幂等历史回放”进入 V2 层级画像。

### 8.2 为什么采用两层模型

直接把 LLM 的 `required_points` 当主画像，会因为措辞变化生成大量一次性知识点。V2 将它们先归一化：

```text
面试主题“RAG 包含检索和生成两个阶段”
→ 稳定主题：RAG

required point“Query 与 Key 进行相似度匹配”
→ 诊断子知识点：检索与召回

required point“回答必须带证据来源”
→ 诊断子知识点：证据引用
```

稳定主题负责回答“整体掌握如何”，子知识点负责回答“为什么得到这个分、下一步补什么”。

### 8.3 可信更新规则

```text
disputed / review_pending
→ 不更新画像

final 且 confidence < 0.70
→ 降权更新

final 且 confidence >= 0.70
→ 完整权重渐进更新
```

掌握度使用平滑更新，不直接等于某一次面试百分比：

```text
新掌握度
= 当前掌握度
 + (本次标准化得分 - 当前掌握度) × 学习率
```

学习率受置信度和题目难度影响。

### 8.4 代码路线

```text
api/profiles.py
→ ProfileService.apply_interview_evaluations
→ profile.py::profile_update_decision
→ profile_taxonomy.py::canonical_topic
→ profile_taxonomy.py::canonical_subtopics
→ profile.py::updated_mastery
→ profile.py::classify_error
→ profile.py::review_verification_progress
→ AbilityProfileModel / ErrorPatternModel / ReviewTaskModel
→ ProfileUpdateEventModel
→ ProfilePanel.jsx / TrainingFocusPanel.jsx
```

迁移路线：

```text
migrations/versions/20260719_0006_profile_review_loop.py
→ migrations/versions/20260729_0007_two_layer_profiles.py
```

## 9. 复杂文档 RAG 与检索解释

### 9.1 图片生成位置

> ![image-20260730004613632](project-handoff-v2.assets/image-20260730004613632.png)

图片生成规格：

- 输入包含 Markdown、TXT、PDF、DOCX。
- 解析层标注标题、段落、列表、代码块、表格、页码。
- 分块层标注 heading path、chunk index、overlap、content hash。
- 存储层标注 PostgreSQL 与 pgvector。
- 查询层分为全文检索和向量检索，两路进入 RRF。
- 输出层显示 citation、source、page、heading、block type、retrieval explanation。
- 证据不足分支进入“显式降级/建议补充资料”。
- 用边界说明框标注“不包含 OCR、版面模型、复杂表格还原和多模态解析”。

### 9.2 代码路线

```text
DocumentParser
→ ParsedSection
→ infer_block_type
→ chunk_sections
→ ChunkDraft
→ KnowledgeService.ingest
→ KnowledgeChunkModel
→ PostgresHybridRetriever
→ reciprocal_rank_fusion
→ RetrievedChunk
→ AnswerService
→ RagPanel 引用卡片
```

### 9.3 Embedding 的准确口径

当前 `DevelopmentEmbeddingGateway` 是本地确定性 feature hashing 基线：

- 支持字符 n-gram 和英文词特征。
- 输出配置维度，默认 1536。
- 进行 L2 归一化。
- 相关文本通常比无关文本具有更高相似度。
- 适合离线测试、低资源演示和可复现回归。

当前默认使用本地 BGE-small-zh，并保留 development 特征哈希 fallback。它已经不是早期纯字面特征哈希方案，但也不能等同于企业级向量服务；正式部署仍需要向量版本治理、重建任务、reranker、权限过滤和更大规模评测。

## 10. 报告历史、趋势和画像消费

### 10.1 图片生成位置

> ![image-20260730012718725](project-handoff-v2.assets/image-20260730012718725.png)

图片生成规格：

- 输入为一场 completed interview 的 Questions、Answers、Rubric 和 Citations。
- 评分层展示 correctness、completeness、reasoning、communication 四维得分。
- 复核路由分为 final、review_pending、disputed。
- final 进入报告和画像；pending/disputed 保留评分但阻止画像污染。
- 报告分为当前详情、历史列表和多轮趋势。
- 应用层计算最终总分，LLM 只提供结构化评分建议。
- 最终指向两层画像和下一轮计划。

### 10.2 代码路线

```text
POST /interviews/{id}/evaluations
→ EvaluationService.evaluate_interview
→ prompts/evaluation_v1.md
→ domain/evaluation.py
→ EvaluationModel / EvaluationReferenceModel
→ EvaluationService.build_report
→ InterviewReportModel
→ GET /reports/history
→ GET /reports/trends
→ ReportHistoryPanel.jsx
→ ProfileService.apply_interview_evaluations
```

走读重点：

- 为什么总分由应用层根据分项重新计算。
- 为什么引用必须来自题目允许的 reference chunk。
- 为什么报告更新采用事务内 upsert，而不是先删除再创建。
- 为什么 Evaluation 可以保留，但不一定更新画像。

## 11. 前端工作台与多知识库状态

### 11.1 前端职责

前端负责：

- 选择、创建和切换知识库。
- 轮询文档索引状态。
- 组织 RAG、面试、报告、画像和系统状态页面。
- 保存当前知识库和按知识库隔离的面试 ID。
- 恢复当前面试和 workflow trace。
- 为长报告提供折叠展示。

前端不负责：

- 计算权威评分。
- 更新掌握度。
- 判断 Evaluation 是否可信。
- 生成复习任务优先级。

### 11.2 多知识库切换路线

```text
KnowledgeBaseSelector
→ main.jsx::switchKnowledgeBase
→ GET /api/v1/knowledge-bases/{id}/documents
→ 更新 knowledgeBase / documents
→ localStorage.activeKnowledgeBaseId
→ restoreActiveInterview(knowledgeBaseId)
→ localStorage.activeInterviewId.{knowledgeBaseId}
```

新建知识库：

```text
点击“新建知识库”
→ 只打开 CreateKnowledgeBaseDialog
→ 取消：不创建、不切换
→ 创建并切换：POST /knowledge-bases
→ 新知识库加入选择器
→ 原知识库仍可选择
```

兼容策略：

- 有资料的知识库始终展示。
- 当前选中的空知识库展示。
- 历史无资料且非当前的空壳不删除，只从日常选择器隐藏。

### 11.3 前端代码地图

| 责任 | 文件 |
| --- | --- |
| 状态编排和页面组合 | `frontend/src/main.jsx` |
| 工作台布局和导航 | `frontend/src/components/AppLayout.jsx` |
| 知识库选择和创建弹窗 | `frontend/src/components/KnowledgeBaseControls.jsx` |
| 文档上传和重建索引 | `frontend/src/components/KnowledgePanel.jsx` |
| RAG 问答和引用展示 | `frontend/src/components/RagPanel.jsx` |
| 面试和工作流轨迹 | `frontend/src/components/InterviewPanel.jsx` |
| 可信评分报告 | `frontend/src/components/EvaluationPanel.jsx` |
| 报告历史和趋势 | `frontend/src/components/ReportHistoryPanel.jsx` |
| 两层画像和复习计划 | `frontend/src/components/ProfilePanel.jsx` |
| 专项训练重点 | `frontend/src/components/TrainingFocusPanel.jsx` |
| 运行态和演示就绪度 | `frontend/src/components/RuntimeInsights.jsx` |
| API 错误与超时处理 | `frontend/src/api/client.js` |
| 报告展示转换 | `frontend/src/utils/report.js` |
| 画像展示转换 | `frontend/src/utils/profile.js` |

## 12. 后端代码地图

### 12.1 入口与接口

| 责任 | 文件 | 主要接口 |
| --- | --- | --- |
| App 初始化 | `src/agent_mentor/main.py` | 注册依赖、路由和启动恢复 |
| 健康与运行态 | `src/agent_mentor/api/health.py` | `/health/live`、`/ready`、`/runtime` |
| 知识库 | `src/agent_mentor/api/knowledge.py` | knowledge-bases、documents、reindex |
| RAG | `src/agent_mentor/api/chat.py` | retrieve、ask、ask/stream |
| 面试 | `src/agent_mentor/api/interviews.py` | create、start、answers、trace、events |
| 评分和报告 | `src/agent_mentor/api/evaluations.py` | evaluations、report、history、trends |
| 画像和训练 | `src/agent_mentor/api/profiles.py` | abilities、errors、tasks、plan、focuses |
| 演示自检 | `src/agent_mentor/api/demo.py` | `/api/v1/demo/readiness` |

### 12.2 Application Service

| Service | 核心职责 |
| --- | --- |
| `KnowledgeService` | 文件校验、状态、解析、分块、embedding、入库、重建索引和中断恢复 |
| `AnswerService` | 检索、证据判断、LLM 回答、引用校验和 fallback |
| `InterviewService` | 会话、计划、题目、checkpoint、幂等答案和轨迹 |
| `EvaluationService` | Rubric 评分、复核路由、报告、历史和趋势 |
| `ProfileService` | 两层画像、错误模式、复习任务、历史回放和训练推荐 |
| `DemoReadinessService` | 只读统计完整演示链路是否具备 |

### 12.3 Domain、Workflows 与 Ports

| 文件 | 走读重点 |
| --- | --- |
| `src/agent_mentor/domain/interview.py` | 状态、难度、题型和合法迁移 |
| `src/agent_mentor/domain/evaluation.py` | Rubric、总分、复核条件 |
| `src/agent_mentor/domain/profile.py` | 可信更新、掌握度、错误分类、复习间隔和排序 |
| `src/agent_mentor/domain/profile_taxonomy.py` | 稳定主题和动态子知识点归一化 |
| `src/agent_mentor/workflows/interview.py` | 节点规格、事件、checkpoint 摘要和状态转换 |
| `src/agent_mentor/ports/embedding_gateway.py` | Embedding 可替换边界 |
| `src/agent_mentor/ports/knowledge_retriever.py` | 检索输入和结果协议 |
| `src/agent_mentor/ports/llm_gateway.py` | LLM 结构化调用边界 |

## 13. 数据模型概览

### 13.1 知识与 RAG

```text
UserModel
└── KnowledgeBaseModel
    └── SourceDocumentModel
        └── KnowledgeChunkModel

ChatSessionModel
├── ChatMessageModel
└── ChatCitationModel
```

### 13.2 面试和报告

```text
InterviewSessionModel
├── InterviewQuestionModel
│   ├── QuestionReferenceModel
│   ├── UserAnswerModel
│   └── EvaluationModel
│       └── EvaluationReferenceModel
├── WorkflowCheckpointModel
└── InterviewReportModel
```

### 13.3 画像和复习

```text
EvaluationModel
└── ProfileUpdateEventModel

UserModel
├── AbilityProfileModel
├── ErrorPatternModel
└── ReviewTaskModel
```

关键约束：

- `UserAnswerModel` 通过幂等键防止重复答案。
- `ProfileUpdateEventModel.evaluation_id` 唯一，防止重复消费评分。
- `AbilityProfileModel` 区分 topic、subtopic 和 legacy。
- `ReviewTaskModel.verification_streak` 记录连续高分验证进度。

## 14. 推荐代码走读路线

### 14.1 第一条：先理解完整闭环

```text
main.py
→ api/knowledge.py
→ KnowledgeService
→ AnswerService
→ InterviewService
→ EvaluationService
→ ProfileService
→ frontend/src/main.jsx
```

目标：先知道系统如何串起来，不在第一遍陷入算法细节。

### 14.2 第二条：学习 RAG 工程

```text
rag/documents.py
→ rag/chunking.py
→ infrastructure/embedding.py
→ infrastructure/retriever.py
→ rag/retrieval.py
→ application/answer_service.py
→ api/chat.py
→ RagPanel.jsx
```

目标：能回答解析、分块、检索融合、引用和证据不足如何处理。

### 14.3 第三条：学习 Agent 工作流

```text
domain/interview.py
→ workflows/interview.py
→ application/interview_service.py
→ infrastructure/database/models.py::WorkflowCheckpointModel
→ api/interviews.py
→ InterviewPanel.jsx
```

目标：能回答状态、checkpoint、interrupt、恢复、幂等和 fallback。

### 14.4 第四条：学习可信评分

```text
prompts/evaluation_v1.md
→ domain/evaluation.py
→ application/evaluation_service.py
→ api/evaluations.py
→ EvaluationPanel.jsx
→ ReportHistoryPanel.jsx
```

目标：能回答 Rubric、引用白名单、复核路由、报告和趋势。

### 14.5 第五条：学习长期画像闭环

```text
domain/profile.py
→ domain/profile_taxonomy.py
→ application/profile_service.py
→ migrations/versions/20260729_0007_two_layer_profiles.py
→ api/profiles.py
→ ProfilePanel.jsx
→ TrainingFocusPanel.jsx
```

目标：能回答主题分为什么变化、子知识点是什么、错误如何形成复习任务、高分如何解决任务。

## 15. 关键设计思路

### 15.1 为什么 RAG 前置

RAG 不是为了给大模型“再塞一点文本”，而是为问答、出题和评分建立可验证证据边界。没有足够证据时，系统应明确降级，而不是把模型已有知识包装成资料结论。

### 15.2 为什么评分结果不能直接等于画像

一次评分可能受题目难度、模型稳定性、引用质量和置信度影响。画像表示长期趋势，因此采用可信门槛、置信权重和渐进更新。

### 15.3 为什么总分由应用层计算

LLM 负责提供结构化分项判断，应用层负责校验范围、重算总分和执行复核规则，避免模型返回自相矛盾的总分。

### 15.4 为什么要 checkpoint 和幂等键

- Checkpoint 解决长流程中断后“从哪里继续”。
- Idempotency-Key 解决重复点击和网络重试导致的重复写入。
- 两者共同保证 Agent 工作流可以恢复而不会重复推进。

### 15.5 为什么不引入重型基础设施

当前规模是单用户本地训练，PostgreSQL 同时承担事务、全文检索、向量检索和历史数据存储，可以显著降低部署成本。只有数据量、并发和 SLA 证明需要时，才拆分队列、搜索和工作流基础设施。

## 16. 运行方式

### 16.1 环境要求

- Windows 10/11。
- WSL2。
- Docker Desktop。
- 建议 16GB 内存。
- DeepSeek/OpenAI-compatible API Key 可选；无 Key 时保留本地降级链路。

### 16.2 配置

复制配置模板：

```powershell
Copy-Item .env.example .env
```

真实 LLM 示例：

```text
AGENT_MENTOR_LLM_BASE_URL=https://api.deepseek.com/v1
AGENT_MENTOR_LLM_API_KEY=你的 Key
AGENT_MENTOR_LLM_DEFAULT_MODEL=deepseek-chat
```

不要将真实 Key 提交到 Git。

### 16.3 启动

在项目根目录执行：

```powershell
docker compose up -d --build
docker compose ps
```

访问：

- 前端：`http://localhost:3000/`
- API 文档：`http://localhost:8000/api/v1/docs`
- 健康检查：`http://localhost:8000/health/ready`

### 16.4 停止

```powershell
docker compose down
```

不要随意增加 `-v`；`docker compose down -v` 会删除 PostgreSQL 和上传文件卷。

## 17. 推荐演示路径

1. 打开总览，确认 LLM 和演示就绪状态。
2. 进入知识库页面，从选择器选已有知识库。
3. 展示资料状态、结构类型和失败重建入口。
4. 执行一次 RAG 问答，展示引用和检索解释。
5. 从能力画像或复习任务选择专项训练主题。
6. 创建三题面试，展示专项训练来源、题型递进和 workflow trace。
7. 使用真实答案或参考答案完成面试。
8. 生成评分报告，展开一题说明扣分原因和缺失点。
9. 打开报告历史和趋势。
10. 打开能力画像，说明稳定主题、诊断子知识点和验证进度。
11. 回到系统状态，说明 fallback 和演示就绪度。

## 18. 质量门禁

### 18.1 前端

```powershell
cd frontend
npm.cmd run build
```

### 18.2 后端

```powershell
$python='C:\Users\19850\AppData\Local\Programs\Python\Python312\python.exe'
& $python -m uv run ruff check .
& $python -m uv run pytest
& $python -m uv run pyright
```

真实数据库集成测试需要配置：

```text
AGENT_MENTOR_TEST_DATABASE_URL=
postgresql+asyncpg://agentmentor:agentmentor@localhost:5432/agentmentor_test
```

当前自动化测试主要覆盖：

- 文档解析、结构化分块和 block type。
- feature hashing 相似度、全文/向量检索、RRF 和引用。
- LLM fallback 和运行态字段。
- 面试状态、checkpoint、题目去重和答案幂等。
- Rubric、置信复核、报告和趋势。
- 两层画像、历史回放、复习任务和训练排序。
- PostgreSQL/pgvector 真实闭环。

## 19. 常见问题与排障

### 19.1 切换知识库后旧资料不见了

旧资料属于另一个知识库。使用顶部“当前知识库”选择器切回。点击新建只打开弹窗，取消不会创建或切换。

### 19.2 文档一直 pending

- 先点击刷新状态。
- 检查 API 日志。
- 如果后台任务曾因进程退出中断，系统启动恢复会将超时任务标为失败。
- 在失败文档上点击“重新索引”。

### 19.3 RAG 显示降级

查看 `generation_mode` 和 `fallback_reason`：

- 证据不足：补充资料或调整问题。
- LLM 调用失败：检查 `.env`、网络和 API 额度。
- 无 Key：系统使用确定性本地基线。

### 19.4 高分后画像不是直接变成高百分比

画像使用长期渐进更新，不等于单次面试得分。检查主题是否一致、Evaluation 是否 final、置信度以及样本权重。

### 19.5 复习任务为什么还没完成

任务通常需要同一主题/子知识点连续两次可信高分。第一次只增加验证进度；中途低分会重置连续次数。

### 19.6 Pyright 或 Ruff 被 Windows 策略阻止

错误码 4551 属于本机应用控制策略，不代表代码失败。可在允许的 Python 环境、WSL 或容器中执行同一质量门禁。

## 20. 当前边界

- 单用户本地画像，没有登录、RBAC 和租户隔离。
- 不包含企业文档权限继承和行列级访问控制。
- 不包含 OCR、布局模型、图片和公式多模态解析。
- 已接入本地 BGE-small-zh，但不包含企业级向量服务治理。
- BackgroundTasks 适合本机演示，不等同于可靠消息队列。
- 工作流节点已显式化，但当前没有使用专用工作流引擎。
- PostgreSQL/pgvector 适合当前规模，尚未验证大规模并发。
- 外部 LLM 的费用、限流和可用性由服务商决定。

## 21. 接手时最该先看的文件

建议顺序：

1. `docs/operations/project-handoff-v2.md`
2. `src/agent_mentor/main.py`
3. `src/agent_mentor/application/interview_service.py`
4. `src/agent_mentor/application/answer_service.py`
5. `src/agent_mentor/application/evaluation_service.py`
6. `src/agent_mentor/application/profile_service.py`
7. `src/agent_mentor/domain/profile_taxonomy.py`
8. `src/agent_mentor/workflows/interview.py`
9. `src/agent_mentor/infrastructure/retriever.py`
10. `src/agent_mentor/infrastructure/database/models.py`
11. `frontend/src/main.jsx`
12. `frontend/src/components/`
13. `tests/integration/test_learning_loop.py`

## 22. 关联文档

- V1 交接：`docs/operations/project-handoff-v1.md`
- V2 路线：`docs/planning/V2开发路线与验收标准.md`
- Phase 7～12 验收：`docs/acceptance/phase-7.md` ～ `phase-12.md`
- 稳定性优化：`docs/acceptance/v2-stability-optimization.md`
- 两层画像设计：`docs/design/v2-two-layer-ability-profile.md`

## 23. 当前维护约定

- V1 和 V2 文档独立维护，不用 V2 内容覆盖 V1 历史。
- 功能描述以当前代码为准，验收报告只作为阶段证据。
- API 路径变化必须同步更新前端和交接文档。
- 数据库字段变化必须通过 Alembic migration。
- 评分和画像规则优先放在 Domain/Application 层，不放在 React。
- 保留无 Key 和 LLM 失败时的可运行降级路径。
- 新功能必须继续满足 Docker Compose 和 16GB 本地开发机约束。
- 文档中的图片生成后，应保留本节“图片生成规格”或将其转为图解说明，避免图片脱离代码事实。

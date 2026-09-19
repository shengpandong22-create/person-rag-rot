# Candidate Evidence Packages — HUMAN REVIEW REQUIRED

- source_dataset: `D:\AgentStudy\personal-rag-bot\evals\datasets\retrieval_regression_v1.jsonl`
- packages: 26
- every candidate below is a **model suggestion**, NOT a label.
- `human_verified` is false for all rows. A reviewer must select the
  correct source(s) and record them as `relevant_sources` manually.
- labels are located by `document_logical_name > heading_path` and carry a
  `content_fingerprint`; no chunk UUID is used as a long-term label.

## Review checklist per case

1. Does any candidate actually answer the question? If none does, decide
   between `partial` / `none` instead of forcing a label.
2. Is the `heading_path` the section that would be cited, or merely a
   nearby section that mentions the right words?
3. Are the `suggested_answer_points` supported by the excerpt, or do they
   need editing before they can serve as a grading rubric?
4. Record the final `relevant_sources` and set `label_origin=human`.

## ret-001

- question: RAG 为什么能降低大模型无依据回答的概率？
- declared answerability: full
- diagnostic_keywords: ['RAG', '证据', '引用']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 14.24)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 二、学员疑问与讨论记录 > Q2：三道防线在 Embedding 强的时候是否仍然具备存在意义？`
- content_fingerprint: `906d4122a87fd025...`
- evidence_excerpt:

  ```
  **学员核心洞察：**
  
  > 即使 Embedding 强，也存在检索出不准确结果、大模型胡编乱造的情况
  
  **回答：**
  
  **三道防线不是因为 Embedding 弱才存在，Embedding 再强也不能去掉。**
  
  | 防线           | 防的根本问题                       | 强 Embedding 能解决吗？                   |
  | -------------- | ---------------------------------- | ----------------------------------------- |
  | 词汇化证据判断 | 检索结果和问题字面无关             | ❌ 不能。强 Embedding 也会召回偏题内容     |
  | 证据门禁       | 证据不够但把模型常识伪装成资料结论 
  ```

- suggested_answer_points (verify before use):
  - 即使 Embedding 强，也存在检索出不准确结果、大模型胡编乱造的情况
  - 三道防线不是因为 Embedding 弱才存在，Embedding 再强也不能去掉。
  - 防线 — 防的根本问题 — 强 Embedding 能解决吗？

### candidate 2 (score 14.24)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 一、教案正文 > 6.3 两层模型 > 分别解决什么问题`
- content_fingerprint: `5e10ae2700491fa6...`
- evidence_excerpt:

  ```
  |                  | 第一层：稳定主题                   | 第二层：动态诊断子知识点                      |
  | ---------------- | ---------------------------------- | --------------------------------------------- |
  | **粒度**         | 粗（10-20 个）                     | 细（50-100+ 个）                              |
  | **回答的问题**   | "用户 RAG 整体能力怎么样？"        | "RAG 里哪里是短板？是 RRF 融合还是引用校验？" |
  | **用途**         | 长期趋势图、下一轮选什么主题     
  ```

- suggested_answer_points (verify before use):
  - 第一层：稳定主题 — 第二层：动态诊断子知识点
  - 粒度 — 粗（10-20 个） — 细（50-100+ 个）
  - 回答的问题 — "用户 RAG 整体能力怎么样？" — "RAG 里哪里是短板？是 RRF 融合还是引用校验？"

### candidate 3 (score 13.01)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.8 第三道防线：引用白名单 > 引用白名单不能做什么`
- content_fingerprint: `c5f36d17cbfd078b...`
- evidence_excerpt:

  ```
  | ❌ 不能                           | 为什么                   |
  | -------------------------------- | ------------------------ |
  | 证明片段完整支持答案中所有 claim | 模型可能断章取义         |
  | 证明文档本身一定正确             | 来源合法性 ≠ 内容正确性  |
  | 证明检索没有漏掉关键证据         | 没召回的东西白名单管不了 |
  | 证明模型没有曲解原文             | 模型可能歪曲 chunk 含义  |
  
  准确表述：**"引用来源合法性校验"**，不是 **"完全消除幻觉"**。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ❌ 不能 — 为什么
  - 证明片段完整支持答案中所有 claim — 模型可能断章取义
  - 证明文档本身一定正确 — 来源合法性 ≠ 内容正确性

### candidate 4 (score 11.77)

- document_logical_name: `第 7 课：工程化专题 + 面试实战`
- heading_path: `第 7 课：工程化专题 + 面试实战 > 一、教案正文 > 7.2 八个故障场景：必须会回答`
- content_fingerprint: `c0d70048f4d71235...`
- evidence_excerpt:

  ```
  | 场景                | 当前处理                                         | 仍然存在的边界                              |
  | ------------------- | ------------------------------------------------ | ------------------------------------------- |
  | 重复提交答案        | 幂等键查询 + DB 唯一约束                         | 不代表所有并发操作都自动串行                |
  | 页面刷新            | GET /interviews/{id} 服务端恢复                  | 浏览器 localStor
  ```

- suggested_answer_points (verify before use):
  - 场景 — 当前处理 — 仍然存在的边界
  - 重复提交答案 — 幂等键查询 + DB 唯一约束 — 不代表所有并发操作都自动串行
  - 页面刷新 — GET /interviews/{id} 服务端恢复 — 浏览器 localStorage 丢失时需重输 session_id

### candidate 5 (score 11.24)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 二、学员疑问与讨论记录 > Q1：当前 RAG 是不是比较 LOW？Embedding 必须改造吗？ > Embedding 层确实基础，但工程防御层不 LOW`
- content_fingerprint: `2000a380bd1c8df2...`
- evidence_excerpt:

  ```
  Embedding 弱不等于整个 RAG 弱。当前 RAG 的工程深度体现在**检索之后**：
  
  ```
  检索（弱） → RRF 融合 → 每文档限额 → 相邻块去重 → 
  词汇化证据判断 → 分数阈值门禁 → 证据不足拒答 →
  LLM 生成 → 引用白名单校验 → 持久化诊断信息
  ```
  
  这些环节不依赖 Embedding 质量，它们是对"检索结果不可信"的防御层。恰恰因为 Embedding 弱，这套防御才更有意义——证明了系统不靠"运气好搜到对的东西"来工作。
  ```

- suggested_answer_points (verify before use):
  - Embedding 弱不等于整个 RAG 弱。当前 RAG 的工程深度体现在检索之后：
  - 检索（弱） → RRF 融合 → 每文档限额 → 相邻块去重 →
  - 词汇化证据判断 → 分数阈值门禁 → 证据不足拒答 →

## ret-002

- question: 向量数据库在个人学习资料问答中承担什么角色？
- declared answerability: full
- diagnostic_keywords: ['向量', '检索', '学习资料']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 9.20)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 1.1 一句话讲清这个项目是什么`
- content_fingerprint: `a97eee5f117d7075...`
- evidence_excerpt:

  ```
  > **AgentMentor 是一个面向个人学习者的 AI 面试训练系统。** 它把学习资料变成可检索证据，通过 RAG 支撑问答和面试出题，再用可信评分更新能力画像和复习任务，形成"学习→训练→评分→画像→下一轮"的闭环。整套系统可在 16GB 普通开发机上通过 Docker Compose 运行。
  ```

- suggested_answer_points (verify before use):
  - AgentMentor 是一个面向个人学习者的 AI 面试训练系统。 它把学习资料变成可检索证据，通过 RAG 支撑问答和面试出题，再用可信评分更新能力画像和复习任务，形成"学习→训练→评分→画像→下一轮"的闭环。整套系统可在 16GB 普通开发机上通过 Docker Compose 运行。

### candidate 2 (score 8.70)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 为什么面试时不能回避边界？`
- content_fingerprint: `f20faf45cf065aa2...`
- evidence_excerpt:

  ```
  每条边界都需要能说出对应的生产方案：
  
  | 边界                 | 需要准备的知识                                               |
  | -------------------- | ------------------------------------------------------------ |
  | 本地 BGE Embedding   | 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界 |
  | 非 LangGraph Runtime | LangGraph 适合什么场景、当前为什么不需用、如何迁移           |
  | 基础文本解析         | OCR（扫描 PDF）、版面分析（多栏/表格）、复杂表格重建——不同格式的难点 |
  ```

- suggested_answer_points (verify before use):
  - 每条边界都需要能说出对应的生产方案：
  - 边界 — 需要准备的知识
  - 本地 BGE Embedding — 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界

### candidate 3 (score 8.70)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.2 为什么需要两路检索`
- content_fingerprint: `90548028082cb2b1...`
- evidence_excerpt:

  ```
  | 查询类型   | 示例                             | 适合的检索           |
  | ---------- | -------------------------------- | -------------------- |
  | 语义改写   | "如何恢复中断的 Agent 流程"      | 向量检索（语义相近） |
  | 精确标识符 | `WorkflowCheckpointModel`、`RRF` | 全文检索（精确匹配） |
  
  技术资料同时包含自然语言和精确标识符，单路召回容易漏失。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 查询类型 — 示例 — 适合的检索
  - 语义改写 — "如何恢复中断的 Agent 流程" — 向量检索（语义相近）
  - 精确标识符 — WorkflowCheckpointModel、RRF — 全文检索（精确匹配）

### candidate 4 (score 8.20)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > 具体计算示例`
- content_fingerprint: `38e56212b02e77e9...`
- evidence_excerpt:

  ```
  假设搜"RRF 融合"，两路返回：
  
  ```
             向量召回排名    全文召回排名
  A（RRF段落）  第1名         第3名
  B（pgvector） 第2名         未召回（∞）
  C（全文检索） 未召回（∞）     第1名
  D（混合检索） 第3名         第2名
  ```
  
  计算：
  ```
  ```

- suggested_answer_points (verify before use):
  - 假设搜"RRF 融合"，两路返回：
  - 向量召回排名    全文召回排名
  - A（RRF段落）  第1名         第3名

### candidate 5 (score 7.00)

- document_logical_name: `第 7 课：工程化专题 + 面试实战`
- heading_path: `第 7 课：工程化专题 + 面试实战 > 一、教案正文 > 7.7 学完整个项目后应该形成的认知`
- content_fingerprint: `303a6e239f475bd6...`
- evidence_excerpt:

  ```
  > AgentMentor 的核心价值不是"用大模型生成三道题"，而是把学习资料、可溯源检索、人机工作流、可信评分和长期画像连接成一个受约束的训练闭环。系统通过应用层规则限制 LLM 的权力，通过 checkpoint 和幂等保证流程状态，通过两层画像控制长期记忆粒度，再通过增量知识目录区分"回答得怎么样"和"资料是否考到"，形成补缺与查漏两类训练信号；并在 16GB 本地约束下选择 PostgreSQL、本地 BGE-small-zh 和模块化单体。它已经是一个真实可运行的个人学习系统，但还不是企业级终态；当前已补同知识库最近历史题目冷却，全量语义题库去重、复杂文档、生产检索评测、租户权限和可靠异步任务是明确的演进方向。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - AgentMentor 的核心价值不是"用大模型生成三道题"，而是把学习资料、可溯源检索、人机工作流、可信评分和长期画像连接成一个受约束的训练闭环。系统通过应用层规则限制 LLM 的权力，通过 checkpoint 和幂等保证流程状态，通过两层画像控制长期记忆粒度，再通过增量知识目录区分"回答得怎么样"和"资料是否考到

## ret-003

- question: 为什么文档 chunk 要保留标题层级？
- declared answerability: full
- diagnostic_keywords: ['标题', '章节', '引用']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 13.36)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.7 重新索引时为什么尽量保留 Chunk ID > 为什么这么做`
- content_fingerprint: `405fb34d5cc05abf...`
- evidence_excerpt:

  ```
  历史面试题和评分可能引用了旧的 Chunk ID。如果每次重建都删除全部 Chunk：
  - 历史评估的 `reference_chunk_ids` 会变成悬空引用
  - 历史报告中的引用来源会丢失
  
  当前方案优先按 `chunk_index` 更新原记录，从而尽量保持引用稳定。
  ```

- suggested_answer_points (verify before use):
  - 历史面试题和评分可能引用了旧的 Chunk ID。如果每次重建都删除全部 Chunk：
  - 历史评估的 reference_chunk_ids 会变成悬空引用
  - 历史报告中的引用来源会丢失

### candidate 2 (score 12.73)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.5 分块策略：为什么不是固定字数切割`
- content_fingerprint: `0f90d67f1ebccba4...`
- evidence_excerpt:

  ```
  当前使用 `chunk_sections` 按**标题边界**切分，而不是按固定字数硬切：
  
  ```
  按标题边界切分（当前做法）：
    "## RRF 公式\nRRF 的基本思想是..."  →  一个完整块
    "## 引用白名单\n引用白名单的作用..."  →  另一个完整块
  
  按固定字数硬切（坏做法）：
    "## RRF 公式\nRRF 的基本思想是[切到一半]..."  →  语义断裂
    "[块2继续]..."  →  上下文丢失
  ```
  ```

- suggested_answer_points (verify before use):
  - 当前使用 chunk_sections 按标题边界切分，而不是按固定字数硬切：
  - 按标题边界切分（当前做法）：
  - "## RRF 公式\nRRF 的基本思想是..."  →  一个完整块

### candidate 3 (score 10.73)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.7 重新索引时为什么尽量保留 Chunk ID`
- content_fingerprint: `d107530c0aeba4b2...`
- evidence_excerpt:

  ```
  ```python
  existing_chunks = {
      chunk.chunk_index: chunk
      for chunk in existing_chunk_rows
  }
  
  for draft, vector in zip(drafts, vectors, strict=True):
      chunk = existing_chunks.pop(draft.chunk_index, None)
      if chunk is None:
          session.add(KnowledgeChunkModel(...))     # 新块 → 新建
      else:
          chunk.content = draft.content              # 已有块 → 更新内容
  ```

- suggested_answer_points (verify before use):
  - existing_chunks = {
  - chunk.chunk_index: chunk
  - for chunk in existing_chunk_rows

### candidate 4 (score 10.73)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.7 重新索引时为什么尽量保留 Chunk ID > 边界`
- content_fingerprint: `3483eaf8f8c2dc13...`
- evidence_excerpt:

  ```
  如果文档大幅重排（段落插入/删除），相同 `chunk_index` 可能已经不是同一语义——这是真实的局限。
  
  面试时可给出递进式改进思路（详见下方疑问记录）。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 如果文档大幅重排（段落插入/删除），相同 chunk_index 可能已经不是同一语义——这是真实的局限。
  - 面试时可给出递进式改进思路（详见下方疑问记录）。

### candidate 5 (score 10.12)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.4 解析阶段：四种格式怎么处理 > 解析输出包含的结构信息`
- content_fingerprint: `68d2876a0086036e...`
- evidence_excerpt:

  ```
  | 字段           | 含义                                              | 面试价值                  |
  | -------------- | ------------------------------------------------- | ------------------------- |
  | `heading_path` | 标题层级路径，如 `["RAG", "混合检索", "RRF公式"]` | 用于增量知识目录构建      |
  | `page_number`  | PDF 页码                                          | 引用时定位原文档          |
  | `chunk_index`  | 块序号                        
  ```

- suggested_answer_points (verify before use):
  - 字段 — 含义 — 面试价值
  - heading_path — 标题层级路径，如 ["RAG", "混合检索", "RRF公式"] — 用于增量知识目录构建
  - page_number — PDF 页码 — 引用时定位原文档

## ret-004

- question: Java 后端转 AI Agent 开发为什么需要学习 RAG？
- declared answerability: full
- diagnostic_keywords: ['Java', 'AI Agent', 'RAG']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 10.59)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.2 为什么需要两路检索`
- content_fingerprint: `90548028082cb2b1...`
- evidence_excerpt:

  ```
  | 查询类型   | 示例                             | 适合的检索           |
  | ---------- | -------------------------------- | -------------------- |
  | 语义改写   | "如何恢复中断的 Agent 流程"      | 向量检索（语义相近） |
  | 精确标识符 | `WorkflowCheckpointModel`、`RRF` | 全文检索（精确匹配） |
  
  技术资料同时包含自然语言和精确标识符，单路召回容易漏失。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 查询类型 — 示例 — 适合的检索
  - 语义改写 — "如何恢复中断的 Agent 流程" — 向量检索（语义相近）
  - 精确标识符 — WorkflowCheckpointModel、RRF — 全文检索（精确匹配）

### candidate 2 (score 8.59)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 一、教案正文 > 6.7 复习任务：为什么需要两次验证 > 为什么不是一次高分就完成`
- content_fingerprint: `085f8db728d81e8e...`
- evidence_excerpt:

  ```
  | 一次高分的问题                   | 两次验证的价值               |
  | -------------------------------- | ---------------------------- |
  | 可能恰好出了用户熟悉的题（运气） | 连续两次才能证明"确实掌握了" |
  | 参考答案演示可能让用户照抄得高分 | 两次不同题目的高分更难作假   |
  | 一次高分直接抹掉长期错误证据     | 需要持续证明才能消除错误记录 |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 一次高分的问题 — 两次验证的价值
  - 可能恰好出了用户熟悉的题（运气） — 连续两次才能证明"确实掌握了"
  - 参考答案演示可能让用户照抄得高分 — 两次不同题目的高分更难作假

### candidate 3 (score 8.57)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 面试重点：为什么需要 ProfileUpdateEvent？`
- content_fingerprint: `7a20ce406e61aff2...`
- evidence_excerpt:

  ```
  它不是多余的日志，而是**画像副作用的审计记录**：
  - 同一 Evaluation 是否已经应用（防重复）
  - 为什么跳过更新（disputed/review_pending）
  - 更新前后掌握度如何变化
  - 使用的是哪一版层级模型
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 它不是多余的日志，而是画像副作用的审计记录：
  - 同一 Evaluation 是否已经应用（防重复）
  - 为什么跳过更新（disputed/review_pending）

### candidate 4 (score 8.00)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 一、教案正文 > 6.7 复习任务：为什么需要两次验证`
- content_fingerprint: `3d7b5ad0dd61d94b...`
- evidence_excerpt:

  ```
  ```python
  def review_verification_progress(current_streak, priority, *, trusted_high_score):
      if not trusted_high_score:
          return 0, priority, False          # 低分 → 重置
      next_streak = min(2, current_streak + 1)
      return next_streak, max(1, priority - 1), next_streak >= 2
  ```
  ```

- suggested_answer_points (verify before use):
  - def review_verification_progress(current_streak, priority, *, trusted_high_score):
  - if not trusted_high_score:
  - return 0, priority, False          # 低分 → 重置

### candidate 5 (score 8.00)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 一、教案正文 > 6.7 复习任务：为什么需要两次验证 > 流程`
- content_fingerprint: `c531ab3d5b922eeb...`
- evidence_excerpt:

  ```
  ```
  第 1 次可信高分 → verification_streak = 1 → 任务保留，优先级降低
  第 2 次连续可信高分 → verification_streak = 2 → 任务完成 ✅
  
  中间低分或不可信结果 → 连续计数重置 → 回到起点
  ```
  ```

- suggested_answer_points (verify before use):
  - 第 1 次可信高分 → verification_streak = 1 → 任务保留，优先级降低
  - 第 2 次连续可信高分 → verification_streak = 2 → 任务完成 ✅
  - 中间低分或不可信结果 → 连续计数重置 → 回到起点

## ret-005

- question: 全文检索和向量检索分别适合什么问题？
- declared answerability: full
- diagnostic_keywords: ['全文', '向量', '混合检索']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 14.07)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > 具体计算示例`
- content_fingerprint: `38e56212b02e77e9...`
- evidence_excerpt:

  ```
  假设搜"RRF 融合"，两路返回：
  
  ```
             向量召回排名    全文召回排名
  A（RRF段落）  第1名         第3名
  B（pgvector） 第2名         未召回（∞）
  C（全文检索） 未召回（∞）     第1名
  D（混合检索） 第3名         第2名
  ```
  
  计算：
  ```
  ```

- suggested_answer_points (verify before use):
  - 假设搜"RRF 融合"，两路返回：
  - 向量召回排名    全文召回排名
  - A（RRF段落）  第1名         第3名

### candidate 2 (score 11.90)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.2 为什么需要两路检索`
- content_fingerprint: `90548028082cb2b1...`
- evidence_excerpt:

  ```
  | 查询类型   | 示例                             | 适合的检索           |
  | ---------- | -------------------------------- | -------------------- |
  | 语义改写   | "如何恢复中断的 Agent 流程"      | 向量检索（语义相近） |
  | 精确标识符 | `WorkflowCheckpointModel`、`RRF` | 全文检索（精确匹配） |
  
  技术资料同时包含自然语言和精确标识符，单路召回容易漏失。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 查询类型 — 示例 — 适合的检索
  - 语义改写 — "如何恢复中断的 Agent 流程" — 向量检索（语义相近）
  - 精确标识符 — WorkflowCheckpointModel、RRF — 全文检索（精确匹配）

### candidate 3 (score 11.37)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 二、学员疑问与讨论记录 > Q1：RRF 排名融合是怎么计算的，为什么要使用 RRF 融合？`
- content_fingerprint: `9ab75490bb8e64a0...`
- evidence_excerpt:

  ```
  **回答：**
  
  核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  
  RRF 不看分数只看排名，公式 `score = Σ 1/(k + rank)`（k=60）。三条核心价值：
  
  | 价值           | 为什么                                   |
  | -------------- | ---------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，只看排名    |
  | **双路有加成** | 两路都召回 → 两个排名参与计算 → 天然加分 |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献        |
  
  ```

- suggested_answer_points (verify before use):
  - 核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  - RRF 不看分数只看排名，公式 score = Σ 1/(k + rank)（k=60）。三条核心价值：
  - 价值 — 为什么

### candidate 4 (score 9.87)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.11 本课自测`
- content_fingerprint: `3ffdc99858af1c11...`
- evidence_excerpt:

  ```
  1. 为什么全文分数和向量分数不能直接相加？
  2. RRF 解决了什么，又没有解决什么？
  3. 引用白名单能做什么、不能做什么？为什么不能说它"完全消除幻觉"？
  4. 证据门禁和引用白名单分别在哪一层防护？各自防什么问题？
  5. 当前 Embedding 弱的情况下，三道防线分别起了什么作用？
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 为什么全文分数和向量分数不能直接相加？
  - RRF 解决了什么，又没有解决什么？
  - 引用白名单能做什么、不能做什么？为什么不能说它"完全消除幻觉"？

### candidate 5 (score 9.27)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > 核心问题：两种分数不在同一尺度上`
- content_fingerprint: `10c946c456e43547...`
- evidence_excerpt:

  ```
  余弦相似度范围 [-1, 1]，全文 `ts_rank_cd` 没有固定上限——一个是归一化的几何距离，一个是自由增长的匹配得分。直接相加会一方权重碾压另一方。
  ```

- suggested_answer_points (verify before use):
  - 余弦相似度范围 [-1, 1]，全文 ts_rank_cd 没有固定上限——一个是归一化的几何距离，一个是自由增长的匹配得分。直接相加会一方权重碾压另一方。

## ret-006

- question: RRF 融合解决了什么排序问题？
- declared answerability: full
- diagnostic_keywords: ['RRF', '排序', '融合']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 20.12)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 解决了什么，没解决什么`
- content_fingerprint: `f82633b37d14f9ca...`
- evidence_excerpt:

  ```
  | ✅ 解决了                             | ❌ 没解决                                 |
  | ------------------------------------ | ---------------------------------------- |
  | 两种异构分数不可比的问题             | 如果两路都没召回正确答案，RRF 也救不了   |
  | 排名融合的稳定性（不依赖原始分尺度） | 检索质量的上限仍取决于两路各自的召回能力 |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ✅ 解决了 — ❌ 没解决
  - 两种异构分数不可比的问题 — 如果两路都没召回正确答案，RRF 也救不了
  - 排名融合的稳定性（不依赖原始分尺度） — 检索质量的上限仍取决于两路各自的召回能力

### candidate 2 (score 16.09)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > 具体计算示例`
- content_fingerprint: `38e56212b02e77e9...`
- evidence_excerpt:

  ```
  假设搜"RRF 融合"，两路返回：
  
  ```
             向量召回排名    全文召回排名
  A（RRF段落）  第1名         第3名
  B（pgvector） 第2名         未召回（∞）
  C（全文检索） 未召回（∞）     第1名
  D（混合检索） 第3名         第2名
  ```
  
  计算：
  ```
  ```

- suggested_answer_points (verify before use):
  - 假设搜"RRF 融合"，两路返回：
  - 向量召回排名    全文召回排名
  - A（RRF段落）  第1名         第3名

### candidate 3 (score 13.75)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 一、教案正文 > 6.3 两层模型 > 分别解决什么问题`
- content_fingerprint: `5e10ae2700491fa6...`
- evidence_excerpt:

  ```
  |                  | 第一层：稳定主题                   | 第二层：动态诊断子知识点                      |
  | ---------------- | ---------------------------------- | --------------------------------------------- |
  | **粒度**         | 粗（10-20 个）                     | 细（50-100+ 个）                              |
  | **回答的问题**   | "用户 RAG 整体能力怎么样？"        | "RAG 里哪里是短板？是 RRF 融合还是引用校验？" |
  | **用途**         | 长期趋势图、下一轮选什么主题     
  ```

- suggested_answer_points (verify before use):
  - 第一层：稳定主题 — 第二层：动态诊断子知识点
  - 粒度 — 粗（10-20 个） — 细（50-100+ 个）
  - 回答的问题 — "用户 RAG 整体能力怎么样？" — "RAG 里哪里是短板？是 RRF 融合还是引用校验？"

### candidate 4 (score 13.75)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 二、学员疑问与讨论记录 > Q2：主题与子知识点分别解决什么问题？`
- content_fingerprint: `4e1c1bd94d5f0651...`
- evidence_excerpt:

  ```
  **回答：**
  
  |            | 第一层：稳定主题             | 第二层：动态诊断子知识点                      |
  | ---------- | ---------------------------- | --------------------------------------------- |
  | 回答的问题 | "用户 RAG 整体能力怎么样？"  | "RAG 里哪里是短板？是 RRF 融合还是引用校验？" |
  | 用途       | 长期趋势图、下一轮选什么主题 | 具体复习建议、错误模式诊断                    |
  | 面试官看到 | "RAG 从 0.40 → 0.47，在进步" | "薄弱点在 RRF 融合"                           |
  
  只用一层的问题：
  - 只有主题层：
  ```

- suggested_answer_points (verify before use):
  - 第一层：稳定主题 — 第二层：动态诊断子知识点
  - 回答的问题 — "用户 RAG 整体能力怎么样？" — "RAG 里哪里是短板？是 RRF 融合还是引用校验？"
  - 用途 — 长期趋势图、下一轮选什么主题 — 具体复习建议、错误模式诊断

### candidate 5 (score 10.39)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 二、学员疑问与讨论记录 > Q1：RRF 排名融合是怎么计算的，为什么要使用 RRF 融合？`
- content_fingerprint: `9ab75490bb8e64a0...`
- evidence_excerpt:

  ```
  **回答：**
  
  核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  
  RRF 不看分数只看排名，公式 `score = Σ 1/(k + rank)`（k=60）。三条核心价值：
  
  | 价值           | 为什么                                   |
  | -------------- | ---------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，只看排名    |
  | **双路有加成** | 两路都召回 → 两个排名参与计算 → 天然加分 |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献        |
  
  ```

- suggested_answer_points (verify before use):
  - 核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  - RRF 不看分数只看排名，公式 score = Σ 1/(k + rank)（k=60）。三条核心价值：
  - 价值 — 为什么

## ret-007

- question: 资料未覆盖问题时系统应该如何回答？
- declared answerability: full
- diagnostic_keywords: ['证据不足', '不伪造引用']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 7.10)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 二、学员疑问与讨论记录 > Q2：文档大幅重排问题，面试中怎么回答？没有企业经验会难吗？ > 面试时这样说的效果`
- content_fingerprint: `1c3aa443b014a084...`
- evidence_excerpt:

  ```
  | 层级              | 你说的                                        | 面试官听到的                             |
  | ----------------- | --------------------------------------------- | ---------------------------------------- |
  | 方案1（内容指纹） | "类似上传阶段的 Hash 去重，延伸到 Chunk 层面" | 他能举一反三，把已有能力延伸到新问题     |
  | 方案2（结构路径） | "标题路径已经在采集了，匹配逻辑从一维变二维"  | 他知道自己系统里有什么数据，不是凭空设计 |
  | 方案3（版本化）   | "企业级方案是版本化引用，历史绑定版本号"      | 他有架构视
  ```

- suggested_answer_points (verify before use):
  - 层级 — 你说的 — 面试官听到的
  - 方案1（内容指纹） — "类似上传阶段的 Hash 去重，延伸到 Chunk 层面" — 他能举一反三，把已有能力延伸到新问题
  - 方案2（结构路径） — "标题路径已经在采集了，匹配逻辑从一维变二维" — 他知道自己系统里有什么数据，不是凭空设计

### candidate 2 (score 6.27)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 二、学员疑问与讨论记录 > Q2：文档大幅重排问题，面试中怎么回答？没有企业经验会难吗？`
- content_fingerprint: `7b837584967655d5...`
- evidence_excerpt:

  ```
  **回答：**
  
  面试官问"文档大幅重排怎么办"，可以直接给出递进式回答——不需要企业经验：
  ```

- suggested_answer_points (verify before use):
  - 面试官问"文档大幅重排怎么办"，可以直接给出递进式回答——不需要企业经验：

### candidate 3 (score 6.00)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 二、学员疑问与讨论记录 > Q2：文档大幅重排问题，面试中怎么回答？没有企业经验会难吗？ > 方案 1：内容指纹（本地就能做，本质是 Hash 去重的延伸）`
- content_fingerprint: `f99b67959f068c4b...`
- evidence_excerpt:

  ```
  ```
  当前：chunk_index=3 匹配 chunk_index=3
        → 文档中间插入一段后，旧的第3块变成了第4块 → 匹配失败 ❌
  
  改进：对每个 chunk 计算 mini 指纹（SHA-256 前 16 位）
        匹配时：先按 index 找，找不到再用指纹遍历邻近 index
        → 内容没变就能匹配上 ✅
  ```
  ```

- suggested_answer_points (verify before use):
  - 当前：chunk_index=3 匹配 chunk_index=3
  - → 文档中间插入一段后，旧的第3块变成了第4块 → 匹配失败 ❌
  - 改进：对每个 chunk 计算 mini 指纹（SHA-256 前 16 位）

### candidate 4 (score 6.00)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 二、学员疑问与讨论记录 > Q2：文档大幅重排问题，面试中怎么回答？没有企业经验会难吗？ > 方案 2：结构路径匹配（当前已有 heading_path）`
- content_fingerprint: `88fcf541c3f1f521...`
- evidence_excerpt:

  ```
  ```
  当前 chunk 已有 heading_path：["RAG", "混合检索", "RRF公式"]
  
  改进逻辑：
    优先匹配：相同的 heading_path + 相近的 chunk_index
    其次匹配：相同的 heading_path（index 不要求精确）
    最后兜底：内容指纹遍历
  ```
  ```

- suggested_answer_points (verify before use):
  - 当前 chunk 已有 heading_path：["RAG", "混合检索", "RRF公式"]
  - 优先匹配：相同的 heading_path + 相近的 chunk_index
  - 其次匹配：相同的 heading_path（index 不要求精确）

### candidate 5 (score 6.00)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 二、学员疑问与讨论记录 > Q2：文档大幅重排问题，面试中怎么回答？没有企业经验会难吗？ > 方案 3：版本化引用（企业级方案，说你理解思路即可）`
- content_fingerprint: `49d35a85e53760cd...`
- evidence_excerpt:

  ```
  ```
  每个 KnowledgeChunk 增加字段：document_version
  
  旧逻辑：interview.question.reference_chunk_id → chunk(id=42)
  新逻辑：interview.question.reference_chunk_id → chunk(id=42, version=v3)
  
  文档重排后：chunk(id=42, version=v4) 是一块新内容
  但历史引用仍然指向 chunk(id=42, version=v3) → 保留在历史快照中
  ```
  ```

- suggested_answer_points (verify before use):
  - 每个 KnowledgeChunk 增加字段：document_version
  - 旧逻辑：interview.question.reference_chunk_id → chunk(id=42)
  - 新逻辑：interview.question.reference_chunk_id → chunk(id=42, version=v3)

## ret-008

- question: 引用校验为什么只能使用本次检索到的 chunk_id？
- declared answerability: full
- diagnostic_keywords: ['chunk_id', '检索上下文', '校验']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 10.48)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.8 第三道防线：引用白名单 > 引用白名单不能做什么`
- content_fingerprint: `c5f36d17cbfd078b...`
- evidence_excerpt:

  ```
  | ❌ 不能                           | 为什么                   |
  | -------------------------------- | ------------------------ |
  | 证明片段完整支持答案中所有 claim | 模型可能断章取义         |
  | 证明文档本身一定正确             | 来源合法性 ≠ 内容正确性  |
  | 证明检索没有漏掉关键证据         | 没召回的东西白名单管不了 |
  | 证明模型没有曲解原文             | 模型可能歪曲 chunk 含义  |
  
  准确表述：**"引用来源合法性校验"**，不是 **"完全消除幻觉"**。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ❌ 不能 — 为什么
  - 证明片段完整支持答案中所有 claim — 模型可能断章取义
  - 证明文档本身一定正确 — 来源合法性 ≠ 内容正确性

### candidate 2 (score 9.94)

- document_logical_name: `第 5 课：可信评分与报告`
- heading_path: `第 5 课：可信评分与报告 > 一、教案正文 > 5.1 先说结论`
- content_fingerprint: `fcbae94ff339a078...`
- evidence_excerpt:

  ```
  LLM 只提供结构化评分建议，**应用层是评分的最终裁判：**
  
  ```
  用户提交回答
      ↓
  LLM 返回四维评分 + 置信度 + 引用
      ↓
  应用层做五件事：
    ① 校验 Rubric（权重必须和为 100）
    ② 校验引用白名单（chunk_id 必须属于本轮检索上下文）
    ③ 应用层重算总分（不直接读取 LLM 返回的 total）
    ④ 判断评分状态（final / review_pending / disputed）
  ```

- suggested_answer_points (verify before use):
  - LLM 只提供结构化评分建议，应用层是评分的最终裁判：
  - LLM 返回四维评分 + 置信度 + 引用
  - 应用层做五件事：

### candidate 3 (score 9.47)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.7 重新索引时为什么尽量保留 Chunk ID > 为什么这么做`
- content_fingerprint: `405fb34d5cc05abf...`
- evidence_excerpt:

  ```
  历史面试题和评分可能引用了旧的 Chunk ID。如果每次重建都删除全部 Chunk：
  - 历史评估的 `reference_chunk_ids` 会变成悬空引用
  - 历史报告中的引用来源会丢失
  
  当前方案优先按 `chunk_index` 更新原记录，从而尽量保持引用稳定。
  ```

- suggested_answer_points (verify before use):
  - 历史面试题和评分可能引用了旧的 Chunk ID。如果每次重建都删除全部 Chunk：
  - 历史评估的 reference_chunk_ids 会变成悬空引用
  - 历史报告中的引用来源会丢失

### candidate 4 (score 9.24)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 公式`
- content_fingerprint: `c0163e197002f710...`
- evidence_excerpt:

  ```
  ```python
  def reciprocal_rank_fusion(ranked_lists, *, rrf_k=60):
      scores = {}
      for ranked in ranked_lists:
          for rank, chunk_id in enumerate(ranked, start=1):
              scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
      return scores
  ```
  
  公式：`score = Σ 1/(k + rank)`
  ```

- suggested_answer_points (verify before use):
  - def reciprocal_rank_fusion(ranked_lists, *, rrf_k=60):
  - scores = {}
  - for ranked in ranked_lists:

### candidate 5 (score 8.77)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 二、学员疑问与讨论记录 > Q1：RRF 排名融合是怎么计算的，为什么要使用 RRF 融合？`
- content_fingerprint: `9ab75490bb8e64a0...`
- evidence_excerpt:

  ```
  **回答：**
  
  核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  
  RRF 不看分数只看排名，公式 `score = Σ 1/(k + rank)`（k=60）。三条核心价值：
  
  | 价值           | 为什么                                   |
  | -------------- | ---------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，只看排名    |
  | **双路有加成** | 两路都召回 → 两个排名参与计算 → 天然加分 |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献        |
  
  ```

- suggested_answer_points (verify before use):
  - 核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  - RRF 不看分数只看排名，公式 score = Σ 1/(k + rank)（k=60）。三条核心价值：
  - 价值 — 为什么

## ret-009

- question: 可信等级可以怎样影响检索排序？
- declared answerability: full
- diagnostic_keywords: ['可信等级', '排序', '语义相关性']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 7.62)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > 具体计算示例`
- content_fingerprint: `38e56212b02e77e9...`
- evidence_excerpt:

  ```
  假设搜"RRF 融合"，两路返回：
  
  ```
             向量召回排名    全文召回排名
  A（RRF段落）  第1名         第3名
  B（pgvector） 第2名         未召回（∞）
  C（全文检索） 未召回（∞）     第1名
  D（混合检索） 第3名         第2名
  ```
  
  计算：
  ```
  ```

- suggested_answer_points (verify before use):
  - 假设搜"RRF 融合"，两路返回：
  - 向量召回排名    全文召回排名
  - A（RRF段落）  第1名         第3名

### candidate 2 (score 7.31)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.4 检索代码的核心流程`
- content_fingerprint: `1810530bdc66ab60...`
- evidence_excerpt:

  ```
  ```python
  # infrastructure/retriever.py
  
  # 1. 向量召回
  vector_candidates = await self._vector_candidates(session, query, normalized)
  
  # 2. 全文召回（仅 HYBRID 模式）
  text_candidates = await self._text_candidates(session, query, normalized)
  
  # 3. RRF 融合
  vector_ranks = {item.chunk.id: item.rank for item in vector_candidates}
  text_ranks = {item.chunk.id: item.rank for item in text_candidates}
  ```

- suggested_answer_points (verify before use):
  - infrastructure/retriever.py
  - vector_candidates = await self._vector_candidates(session, query, normalized)
  - 2. 全文召回（仅 HYBRID 模式）

### candidate 3 (score 4.61)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.2 为什么需要两路检索`
- content_fingerprint: `90548028082cb2b1...`
- evidence_excerpt:

  ```
  | 查询类型   | 示例                             | 适合的检索           |
  | ---------- | -------------------------------- | -------------------- |
  | 语义改写   | "如何恢复中断的 Agent 流程"      | 向量检索（语义相近） |
  | 精确标识符 | `WorkflowCheckpointModel`、`RRF` | 全文检索（精确匹配） |
  
  技术资料同时包含自然语言和精确标识符，单路召回容易漏失。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 查询类型 — 示例 — 适合的检索
  - 语义改写 — "如何恢复中断的 Agent 流程" — 向量检索（语义相近）
  - 精确标识符 — WorkflowCheckpointModel、RRF — 全文检索（精确匹配）

### candidate 4 (score 4.61)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 解决了什么，没解决什么`
- content_fingerprint: `f82633b37d14f9ca...`
- evidence_excerpt:

  ```
  | ✅ 解决了                             | ❌ 没解决                                 |
  | ------------------------------------ | ---------------------------------------- |
  | 两种异构分数不可比的问题             | 如果两路都没召回正确答案，RRF 也救不了   |
  | 排名融合的稳定性（不依赖原始分尺度） | 检索质量的上限仍取决于两路各自的召回能力 |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ✅ 解决了 — ❌ 没解决
  - 两种异构分数不可比的问题 — 如果两路都没召回正确答案，RRF 也救不了
  - 排名融合的稳定性（不依赖原始分尺度） — 检索质量的上限仍取决于两路各自的召回能力

### candidate 5 (score 4.61)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.8 第三道防线：引用白名单 > 引用白名单不能做什么`
- content_fingerprint: `c5f36d17cbfd078b...`
- evidence_excerpt:

  ```
  | ❌ 不能                           | 为什么                   |
  | -------------------------------- | ------------------------ |
  | 证明片段完整支持答案中所有 claim | 模型可能断章取义         |
  | 证明文档本身一定正确             | 来源合法性 ≠ 内容正确性  |
  | 证明检索没有漏掉关键证据         | 没召回的东西白名单管不了 |
  | 证明模型没有曲解原文             | 模型可能歪曲 chunk 含义  |
  
  准确表述：**"引用来源合法性校验"**，不是 **"完全消除幻觉"**。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ❌ 不能 — 为什么
  - 证明片段完整支持答案中所有 claim — 模型可能断章取义
  - 证明文档本身一定正确 — 来源合法性 ≠ 内容正确性

## ret-010

- question: 为什么不能把 RAG 描述成保证答案绝对正确？
- declared answerability: full
- diagnostic_keywords: ['不能保证', '证据', '可追溯']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 13.00)

- document_logical_name: `第 7 课：工程化专题 + 面试实战`
- heading_path: `第 7 课：工程化专题 + 面试实战 > 一、教案正文 > 7.3 企业级 RAG 演进路线 > 为什么不能一开始就拆微服务`
- content_fingerprint: `b99d9aa6fe73d1f4...`
- evidence_excerpt:

  ```
  企业化的优先级应是**权限、数据质量和评测证据**，而不是服务数量。先保持模块边界，通过接口逐步替换基础设施；只有独立扩缩容、故障隔离或团队所有权出现明确需求时再拆服务。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 企业化的优先级应是权限、数据质量和评测证据，而不是服务数量。先保持模块边界，通过接口逐步替换基础设施；只有独立扩缩容、故障隔离或团队所有权出现明确需求时再拆服务。

### candidate 2 (score 10.80)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 的三条核心价值`
- content_fingerprint: `f490a5d69dd04ba9...`
- evidence_excerpt:

  ```
  | 价值           | 为什么                                            |
  | -------------- | ------------------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，RRF 只看排名         |
  | **双路有加成** | 两路都召回 → 两个排名都参与计算 → 天然加分        |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献，不会被粗暴截断 |
  ```

- suggested_answer_points (verify before use):
  - 价值 — 为什么
  - 量纲无关 — 不管原始分是 0.72 还是 9500，RRF 只看排名
  - 双路有加成 — 两路都召回 → 两个排名都参与计算 → 天然加分

### candidate 3 (score 10.80)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 解决了什么，没解决什么`
- content_fingerprint: `f82633b37d14f9ca...`
- evidence_excerpt:

  ```
  | ✅ 解决了                             | ❌ 没解决                                 |
  | ------------------------------------ | ---------------------------------------- |
  | 两种异构分数不可比的问题             | 如果两路都没召回正确答案，RRF 也救不了   |
  | 排名融合的稳定性（不依赖原始分尺度） | 检索质量的上限仍取决于两路各自的召回能力 |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ✅ 解决了 — ❌ 没解决
  - 两种异构分数不可比的问题 — 如果两路都没召回正确答案，RRF 也救不了
  - 排名融合的稳定性（不依赖原始分尺度） — 检索质量的上限仍取决于两路各自的召回能力

### candidate 4 (score 10.55)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.8 第三道防线：引用白名单 > 引用白名单不能做什么`
- content_fingerprint: `c5f36d17cbfd078b...`
- evidence_excerpt:

  ```
  | ❌ 不能                           | 为什么                   |
  | -------------------------------- | ------------------------ |
  | 证明片段完整支持答案中所有 claim | 模型可能断章取义         |
  | 证明文档本身一定正确             | 来源合法性 ≠ 内容正确性  |
  | 证明检索没有漏掉关键证据         | 没召回的东西白名单管不了 |
  | 证明模型没有曲解原文             | 模型可能歪曲 chunk 含义  |
  
  准确表述：**"引用来源合法性校验"**，不是 **"完全消除幻觉"**。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ❌ 不能 — 为什么
  - 证明片段完整支持答案中所有 claim — 模型可能断章取义
  - 证明文档本身一定正确 — 来源合法性 ≠ 内容正确性

### candidate 5 (score 10.00)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 公式`
- content_fingerprint: `c0163e197002f710...`
- evidence_excerpt:

  ```
  ```python
  def reciprocal_rank_fusion(ranked_lists, *, rrf_k=60):
      scores = {}
      for ranked in ranked_lists:
          for rank, chunk_id in enumerate(ranked, start=1):
              scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
      return scores
  ```
  
  公式：`score = Σ 1/(k + rank)`
  ```

- suggested_answer_points (verify before use):
  - def reciprocal_rank_fusion(ranked_lists, *, rrf_k=60):
  - scores = {}
  - for ranked in ranked_lists:

## ret-011

- question: 文档上传时为什么要计算 SHA-256？
- declared answerability: full
- diagnostic_keywords: ['SHA-256', '重复', '版本']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 14.75)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.2 上传阶段：三个安全措施 > 面试要能讲清的三点`
- content_fingerprint: `63c965b7ca5db65e...`
- evidence_excerpt:

  ```
  | 措施              | 防什么                                | 为什么不能只靠前端                 |
  | ----------------- | ------------------------------------- | ---------------------------------- |
  | 后端校验扩展名    | 上传可执行文件/非预期格式             | 前端校验可被绕过                   |
  | `Path(name).name` | 路径穿越攻击（`../../../etc/passwd`） | 直接用原始文件名可能访问预期外路径 |
  | SHA-256 去重      | 重复上传浪费存储和索引                | 按文件名覆盖会丢失版本历史        
  ```

- suggested_answer_points (verify before use):
  - 措施 — 防什么 — 为什么不能只靠前端
  - 后端校验扩展名 — 上传可执行文件/非预期格式 — 前端校验可被绕过
  - Path(name).name — 路径穿越攻击（../../../etc/passwd） — 直接用原始文件名可能访问预期外路径

### candidate 2 (score 9.39)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 二、学员疑问与讨论记录 > Q1：RRF 排名融合是怎么计算的，为什么要使用 RRF 融合？`
- content_fingerprint: `9ab75490bb8e64a0...`
- evidence_excerpt:

  ```
  **回答：**
  
  核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  
  RRF 不看分数只看排名，公式 `score = Σ 1/(k + rank)`（k=60）。三条核心价值：
  
  | 价值           | 为什么                                   |
  | -------------- | ---------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，只看排名    |
  | **双路有加成** | 两路都召回 → 两个排名参与计算 → 天然加分 |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献        |
  
  ```

- suggested_answer_points (verify before use):
  - 核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  - RRF 不看分数只看排名，公式 score = Σ 1/(k + rank)（k=60）。三条核心价值：
  - 价值 — 为什么

### candidate 3 (score 8.73)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.1 先说结论`
- content_fingerprint: `fb1ad6a0cea0ebdc...`
- evidence_excerpt:

  ```
  一条完整的知识入库链路：
  
  ```
  用户上传文件
    → 后端二次校验文件类型
    → SHA-256 内容去重（同内容拒绝，同名不同内容形成新版本）
    → 解析（Markdown/TXT/PDF/DOCX → 纯文本+结构信息）
    → 分块（按标题边界切分，带 overlap 防语义断裂）
    → Embedding（文本→向量，当前默认 BGE-small-zh，测试/无模型环境可降级到 development）
    → 双重索引（pgvector 向量 + PostgreSQL tsvector 全文）
    → 增量目录同步（提取标题路径为 KnowledgeCatalogPoint）
    → 状态变为 READY
  ```

- suggested_answer_points (verify before use):
  - 一条完整的知识入库链路：
  - → 后端二次校验文件类型
  - → SHA-256 内容去重（同内容拒绝，同名不同内容形成新版本）

### candidate 4 (score 8.36)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.7 重新索引时为什么尽量保留 Chunk ID > 边界`
- content_fingerprint: `3483eaf8f8c2dc13...`
- evidence_excerpt:

  ```
  如果文档大幅重排（段落插入/删除），相同 `chunk_index` 可能已经不是同一语义——这是真实的局限。
  
  面试时可给出递进式改进思路（详见下方疑问记录）。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 如果文档大幅重排（段落插入/删除），相同 chunk_index 可能已经不是同一语义——这是真实的局限。
  - 面试时可给出递进式改进思路（详见下方疑问记录）。

### candidate 5 (score 8.03)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 为什么面试时不能回避边界？`
- content_fingerprint: `f20faf45cf065aa2...`
- evidence_excerpt:

  ```
  每条边界都需要能说出对应的生产方案：
  
  | 边界                 | 需要准备的知识                                               |
  | -------------------- | ------------------------------------------------------------ |
  | 本地 BGE Embedding   | 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界 |
  | 非 LangGraph Runtime | LangGraph 适合什么场景、当前为什么不需用、如何迁移           |
  | 基础文本解析         | OCR（扫描 PDF）、版面分析（多栏/表格）、复杂表格重建——不同格式的难点 |
  ```

- suggested_answer_points (verify before use):
  - 每条边界都需要能说出对应的生产方案：
  - 边界 — 需要准备的知识
  - 本地 BGE Embedding — 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界

## ret-012

- question: 旧版本文档为什么要退出默认检索范围？
- declared answerability: full
- diagnostic_keywords: ['旧版本', '默认检索', '版本']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 12.50)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.2 上传阶段：三个安全措施 > 版本管理`
- content_fingerprint: `946324068f4d15be...`
- evidence_excerpt:

  ```
  同名但内容不同的文件 → **形成新版本，旧版本设为非活跃**
  
  这比简单覆盖更适合知识追踪——可以追溯"某个回答引用的是哪个版本的资料"。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 同名但内容不同的文件 → 形成新版本，旧版本设为非活跃
  - 这比简单覆盖更适合知识追踪——可以追溯"某个回答引用的是哪个版本的资料"。

### candidate 2 (score 9.05)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 二、学员疑问与讨论记录 > Q1：RRF 排名融合是怎么计算的，为什么要使用 RRF 融合？`
- content_fingerprint: `9ab75490bb8e64a0...`
- evidence_excerpt:

  ```
  **回答：**
  
  核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  
  RRF 不看分数只看排名，公式 `score = Σ 1/(k + rank)`（k=60）。三条核心价值：
  
  | 价值           | 为什么                                   |
  | -------------- | ---------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，只看排名    |
  | **双路有加成** | 两路都召回 → 两个排名参与计算 → 天然加分 |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献        |
  
  ```

- suggested_answer_points (verify before use):
  - 核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  - RRF 不看分数只看排名，公式 score = Σ 1/(k + rank)（k=60）。三条核心价值：
  - 价值 — 为什么

### candidate 3 (score 8.30)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 为什么面试时不能回避边界？`
- content_fingerprint: `f20faf45cf065aa2...`
- evidence_excerpt:

  ```
  每条边界都需要能说出对应的生产方案：
  
  | 边界                 | 需要准备的知识                                               |
  | -------------------- | ------------------------------------------------------------ |
  | 本地 BGE Embedding   | 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界 |
  | 非 LangGraph Runtime | LangGraph 适合什么场景、当前为什么不需用、如何迁移           |
  | 基础文本解析         | OCR（扫描 PDF）、版面分析（多栏/表格）、复杂表格重建——不同格式的难点 |
  ```

- suggested_answer_points (verify before use):
  - 每条边界都需要能说出对应的生产方案：
  - 边界 — 需要准备的知识
  - 本地 BGE Embedding — 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界

### candidate 4 (score 8.25)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.7 重新索引时为什么尽量保留 Chunk ID > 边界`
- content_fingerprint: `3483eaf8f8c2dc13...`
- evidence_excerpt:

  ```
  如果文档大幅重排（段落插入/删除），相同 `chunk_index` 可能已经不是同一语义——这是真实的局限。
  
  面试时可给出递进式改进思路（详见下方疑问记录）。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 如果文档大幅重排（段落插入/删除），相同 chunk_index 可能已经不是同一语义——这是真实的局限。
  - 面试时可给出递进式改进思路（详见下方疑问记录）。

### candidate 5 (score 8.25)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.5 检索后处理：为什么还要限额和去重 > 每文档限额（max_chunks_per_document）`
- content_fingerprint: `2f46a5152e27d796...`
- evidence_excerpt:

  ```
  不加限制：某篇 100 页文档占全部 Top-K → 来源单一。  
  加限制后：每篇最多贡献 N 个 chunk → 来源多样化。
  ```

- suggested_answer_points (verify before use):
  - 不加限制：某篇 100 页文档占全部 Top-K → 来源单一。
  - 加限制后：每篇最多贡献 N 个 chunk → 来源多样化。

## ret-013

- question: Prompt Injection 文档指令为什么不能覆盖系统规则？
- declared answerability: full
- diagnostic_keywords: ['Prompt Injection', '系统规则', '不可信数据']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 8.80)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 的三条核心价值`
- content_fingerprint: `f490a5d69dd04ba9...`
- evidence_excerpt:

  ```
  | 价值           | 为什么                                            |
  | -------------- | ------------------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，RRF 只看排名         |
  | **双路有加成** | 两路都召回 → 两个排名都参与计算 → 天然加分        |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献，不会被粗暴截断 |
  ```

- suggested_answer_points (verify before use):
  - 价值 — 为什么
  - 量纲无关 — 不管原始分是 0.72 还是 9500，RRF 只看排名
  - 双路有加成 — 两路都召回 → 两个排名都参与计算 → 天然加分

### candidate 2 (score 8.30)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 解决了什么，没解决什么`
- content_fingerprint: `f82633b37d14f9ca...`
- evidence_excerpt:

  ```
  | ✅ 解决了                             | ❌ 没解决                                 |
  | ------------------------------------ | ---------------------------------------- |
  | 两种异构分数不可比的问题             | 如果两路都没召回正确答案，RRF 也救不了   |
  | 排名融合的稳定性（不依赖原始分尺度） | 检索质量的上限仍取决于两路各自的召回能力 |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ✅ 解决了 — ❌ 没解决
  - 两种异构分数不可比的问题 — 如果两路都没召回正确答案，RRF 也救不了
  - 排名融合的稳定性（不依赖原始分尺度） — 检索质量的上限仍取决于两路各自的召回能力

### candidate 3 (score 8.00)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.5 分块策略：为什么不是固定字数切割`
- content_fingerprint: `0f90d67f1ebccba4...`
- evidence_excerpt:

  ```
  当前使用 `chunk_sections` 按**标题边界**切分，而不是按固定字数硬切：
  
  ```
  按标题边界切分（当前做法）：
    "## RRF 公式\nRRF 的基本思想是..."  →  一个完整块
    "## 引用白名单\n引用白名单的作用..."  →  另一个完整块
  
  按固定字数硬切（坏做法）：
    "## RRF 公式\nRRF 的基本思想是[切到一半]..."  →  语义断裂
    "[块2继续]..."  →  上下文丢失
  ```
  ```

- suggested_answer_points (verify before use):
  - 当前使用 chunk_sections 按标题边界切分，而不是按固定字数硬切：
  - 按标题边界切分（当前做法）：
  - "## RRF 公式\nRRF 的基本思想是..."  →  一个完整块

### candidate 4 (score 8.00)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.5 分块策略：为什么不是固定字数切割 > 为什么还要加 overlap？`
- content_fingerprint: `4a6f59b18f67696a...`
- evidence_excerpt:

  ```
  标题之间可能有逻辑承接段（如"如上所述"、"因此"），overlap 保证跨标题的上下文不丢失。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 标题之间可能有逻辑承接段（如"如上所述"、"因此"），overlap 保证跨标题的上下文不丢失。

### candidate 5 (score 8.00)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 公式`
- content_fingerprint: `c0163e197002f710...`
- evidence_excerpt:

  ```
  ```python
  def reciprocal_rank_fusion(ranked_lists, *, rrf_k=60):
      scores = {}
      for ranked in ranked_lists:
          for rank, chunk_id in enumerate(ranked, start=1):
              scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
      return scores
  ```
  
  公式：`score = Σ 1/(k + rank)`
  ```

- suggested_answer_points (verify before use):
  - def reciprocal_rank_fusion(ranked_lists, *, rrf_k=60):
  - scores = {}
  - for ranked in ranked_lists:

## ret-014

- question: SSE 问答流需要哪些终止事件？
- declared answerability: full
- diagnostic_keywords: ['SSE', 'answer.completed', 'answer.failed']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 3.36)

- document_logical_name: `第 4 课：可恢复模拟面试工作流`
- heading_path: `第 4 课：可恢复模拟面试工作流 > 一、教案正文 > 4.3 面试启动流程`
- content_fingerprint: `528abb24fdaec045...`
- evidence_excerpt:

  ```
  ```python
  async def create_interview(self, *, knowledge_base_id, topic, difficulty, ...):
      interview = InterviewSessionModel(status=InterviewStatus.CREATED, ...)
      session.add(interview)
  
      assert_transition(interview.status, InterviewStatus.WAITING_FOR_ANSWER)
      interview.status = InterviewStatus.WAITING_FOR_ANSWER
  
      await self._checkpoint(db, load_profile(...))
      await self._checkp
  ```

- suggested_answer_points (verify before use):
  - async def create_interview(self, *, knowledge_base_id, topic, difficulty, ...):
  - interview = InterviewSessionModel(status=InterviewStatus.CREATED, ...)
  - session.add(interview)

### candidate 2 (score 3.36)

- document_logical_name: `第 5 课：可信评分与报告`
- heading_path: `第 5 课：可信评分与报告 > 一、教案正文 > 5.5 评分代码中的可信约束`
- content_fingerprint: `ce6d645d5eac37f8...`
- evidence_excerpt:

  ```
  ```python
  # 1. 获取本题合法引用
  allowed_references = await self._question_reference_ids(db, question.id)
  
  # 2. LLM 评分
  output = await self._evaluate_with_llm_or_fallback(question, answer, allowed_references)
  
  # 3. 引用白名单
  self._assert_allowed_references(output.reference_chunk_ids, allowed_references)
  
  # 4. 复核判断
  reasons = review_reasons_for(output)
  ```

- suggested_answer_points (verify before use):
  - 1. 获取本题合法引用
  - allowed_references = await self._question_reference_ids(db, question.id)
  - 2. LLM 评分

### candidate 3 (score 2.66)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 一、教案正文 > 6.7 复习任务：为什么需要两次验证 > 为什么不是一次高分就完成`
- content_fingerprint: `085f8db728d81e8e...`
- evidence_excerpt:

  ```
  | 一次高分的问题                   | 两次验证的价值               |
  | -------------------------------- | ---------------------------- |
  | 可能恰好出了用户熟悉的题（运气） | 连续两次才能证明"确实掌握了" |
  | 参考答案演示可能让用户照抄得高分 | 两次不同题目的高分更难作假   |
  | 一次高分直接抹掉长期错误证据     | 需要持续证明才能消除错误记录 |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 一次高分的问题 — 两次验证的价值
  - 可能恰好出了用户熟悉的题（运气） — 连续两次才能证明"确实掌握了"
  - 参考答案演示可能让用户照抄得高分 — 两次不同题目的高分更难作假

### candidate 4 (score 2.30)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.2 为什么需要两路检索`
- content_fingerprint: `90548028082cb2b1...`
- evidence_excerpt:

  ```
  | 查询类型   | 示例                             | 适合的检索           |
  | ---------- | -------------------------------- | -------------------- |
  | 语义改写   | "如何恢复中断的 Agent 流程"      | 向量检索（语义相近） |
  | 精确标识符 | `WorkflowCheckpointModel`、`RRF` | 全文检索（精确匹配） |
  
  技术资料同时包含自然语言和精确标识符，单路召回容易漏失。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 查询类型 — 示例 — 适合的检索
  - 语义改写 — "如何恢复中断的 Agent 流程" — 向量检索（语义相近）
  - 精确标识符 — WorkflowCheckpointModel、RRF — 全文检索（精确匹配）

### candidate 5 (score 2.30)

- document_logical_name: `第 7 课：工程化专题 + 面试实战`
- heading_path: `第 7 课：工程化专题 + 面试实战 > 一、教案正文 > 7.1 五个最能体现工程能力的专题 > 专题 5：历史可追溯需要稳定标识和版本`
- content_fingerprint: `1b17c283c0f26952...`
- evidence_excerpt:

  ```
  | 对象       | 稳定标识机制                                           |
  | ---------- | ------------------------------------------------------ |
  | 文档       | 内容 SHA-256 + 版本号（同名不同内容形成新版本）        |
  | Chunk      | 重建尽量保留 ID（按 chunk_index 匹配，按内容更新）     |
  | Evaluation | 保存 model_name + prompt_version（如 "evaluation_v1"） |
  | 画像更新   | 保存 hierarchy_version（V2） + 变化详情                |
  | 报告       | 保留多轮历史（不覆盖，可追溯趋势）
  ```

- suggested_answer_points (verify before use):
  - 对象 — 稳定标识机制
  - 文档 — 内容 SHA-256 + 版本号（同名不同内容形成新版本）
  - Chunk — 重建尽量保留 ID（按 chunk_index 匹配，按内容更新）

## ret-015

- question: 检索候选为什么需要记录融合分数？
- declared answerability: full
- diagnostic_keywords: ['候选', '融合分数', '追溯']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 11.16)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 解决了什么，没解决什么`
- content_fingerprint: `f82633b37d14f9ca...`
- evidence_excerpt:

  ```
  | ✅ 解决了                             | ❌ 没解决                                 |
  | ------------------------------------ | ---------------------------------------- |
  | 两种异构分数不可比的问题             | 如果两路都没召回正确答案，RRF 也救不了   |
  | 排名融合的稳定性（不依赖原始分尺度） | 检索质量的上限仍取决于两路各自的召回能力 |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ✅ 解决了 — ❌ 没解决
  - 两种异构分数不可比的问题 — 如果两路都没召回正确答案，RRF 也救不了
  - 排名融合的稳定性（不依赖原始分尺度） — 检索质量的上限仍取决于两路各自的召回能力

### candidate 2 (score 11.16)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 二、学员疑问与讨论记录 > Q1：RRF 排名融合是怎么计算的，为什么要使用 RRF 融合？`
- content_fingerprint: `9ab75490bb8e64a0...`
- evidence_excerpt:

  ```
  **回答：**
  
  核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  
  RRF 不看分数只看排名，公式 `score = Σ 1/(k + rank)`（k=60）。三条核心价值：
  
  | 价值           | 为什么                                   |
  | -------------- | ---------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，只看排名    |
  | **双路有加成** | 两路都召回 → 两个排名参与计算 → 天然加分 |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献        |
  
  ```

- suggested_answer_points (verify before use):
  - 核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  - RRF 不看分数只看排名，公式 score = Σ 1/(k + rank)（k=60）。三条核心价值：
  - 价值 — 为什么

### candidate 3 (score 10.87)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 的三条核心价值`
- content_fingerprint: `f490a5d69dd04ba9...`
- evidence_excerpt:

  ```
  | 价值           | 为什么                                            |
  | -------------- | ------------------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，RRF 只看排名         |
  | **双路有加成** | 两路都召回 → 两个排名都参与计算 → 天然加分        |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献，不会被粗暴截断 |
  ```

- suggested_answer_points (verify before use):
  - 价值 — 为什么
  - 量纲无关 — 不管原始分是 0.72 还是 9500，RRF 只看排名
  - 双路有加成 — 两路都召回 → 两个排名都参与计算 → 天然加分

### candidate 4 (score 10.59)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.2 为什么需要两路检索`
- content_fingerprint: `90548028082cb2b1...`
- evidence_excerpt:

  ```
  | 查询类型   | 示例                             | 适合的检索           |
  | ---------- | -------------------------------- | -------------------- |
  | 语义改写   | "如何恢复中断的 Agent 流程"      | 向量检索（语义相近） |
  | 精确标识符 | `WorkflowCheckpointModel`、`RRF` | 全文检索（精确匹配） |
  
  技术资料同时包含自然语言和精确标识符，单路召回容易漏失。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 查询类型 — 示例 — 适合的检索
  - 语义改写 — "如何恢复中断的 Agent 流程" — 向量检索（语义相近）
  - 精确标识符 — WorkflowCheckpointModel、RRF — 全文检索（精确匹配）

### candidate 5 (score 10.57)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > 具体计算示例`
- content_fingerprint: `38e56212b02e77e9...`
- evidence_excerpt:

  ```
  假设搜"RRF 融合"，两路返回：
  
  ```
             向量召回排名    全文召回排名
  A（RRF段落）  第1名         第3名
  B（pgvector） 第2名         未召回（∞）
  C（全文检索） 未召回（∞）     第1名
  D（混合检索） 第3名         第2名
  ```
  
  计算：
  ```
  ```

- suggested_answer_points (verify before use):
  - 假设搜"RRF 融合"，两路返回：
  - 向量召回排名    全文召回排名
  - A（RRF段落）  第1名         第3名

## ret-016

- question: 16GB 开发机资源约束对架构选型有什么影响？
- declared answerability: full
- diagnostic_keywords: ['16GB', 'Docker Compose', '资源']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 10.71)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 1.1 一句话讲清这个项目是什么`
- content_fingerprint: `a97eee5f117d7075...`
- evidence_excerpt:

  ```
  > **AgentMentor 是一个面向个人学习者的 AI 面试训练系统。** 它把学习资料变成可检索证据，通过 RAG 支撑问答和面试出题，再用可信评分更新能力画像和复习任务，形成"学习→训练→评分→画像→下一轮"的闭环。整套系统可在 16GB 普通开发机上通过 Docker Compose 运行。
  ```

- suggested_answer_points (verify before use):
  - AgentMentor 是一个面向个人学习者的 AI 面试训练系统。 它把学习资料变成可检索证据，通过 RAG 支撑问答和面试出题，再用可信评分更新能力画像和复习任务，形成"学习→训练→评分→画像→下一轮"的闭环。整套系统可在 16GB 普通开发机上通过 Docker Compose 运行。

### candidate 2 (score 5.00)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 1.2 六层架构（先建立系统地图）`
- content_fingerprint: `9d2290297c59a0e0...`
- evidence_excerpt:

  ```
  ```
  ┌──────────────────────────────────────────────┐
  │  交互层    React 前端 (知识库/问答/面试/画像)     │
  ├──────────────────────────────────────────────┤
  │  接口层    FastAPI Router (7个路由)              │
  │           chat / knowledge / interviews /      │
  │           evaluations / profiles / demo        │
  ├──────────────────────────────────────────────┤
  │  应用层    Service (编排中心)                    │
  │           An
  ```

- suggested_answer_points (verify before use):
  - ┌──────────────────────────────────────────────┐
  - │  交互层    React 前端 (知识库/问答/面试/画像)     │
  - ├──────────────────────────────────────────────┤

### candidate 3 (score 4.54)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 为什么面试时不能回避边界？`
- content_fingerprint: `f20faf45cf065aa2...`
- evidence_excerpt:

  ```
  每条边界都需要能说出对应的生产方案：
  
  | 边界                 | 需要准备的知识                                               |
  | -------------------- | ------------------------------------------------------------ |
  | 本地 BGE Embedding   | 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界 |
  | 非 LangGraph Runtime | LangGraph 适合什么场景、当前为什么不需用、如何迁移           |
  | 基础文本解析         | OCR（扫描 PDF）、版面分析（多栏/表格）、复杂表格重建——不同格式的难点 |
  ```

- suggested_answer_points (verify before use):
  - 每条边界都需要能说出对应的生产方案：
  - 边界 — 需要准备的知识
  - 本地 BGE Embedding — 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界

### candidate 4 (score 4.54)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 关键区分：它不是什么`
- content_fingerprint: `5110b97ba0723a51...`
- evidence_excerpt:

  ```
  | ❌ 不是               | ✅ 而是                                   |
  | -------------------- | ---------------------------------------- |
  | 调个 API 聊天的 Demo | 有状态、有规则、有长期记忆的训练系统     |
  | 通用 ChatGPT 替代品  | 把大模型包装为有领域数据约束的训练应用   |
  | LangGraph 运行时     | 自己实现显式节点+checkpoint 的人机工作流 |
  | 企业多租户平台       | 模块化单体，本机用户优先                 |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ❌ 不是 — ✅ 而是
  - 调个 API 聊天的 Demo — 有状态、有规则、有长期记忆的训练系统
  - 通用 ChatGPT 替代品 — 把大模型包装为有领域数据约束的训练应用

### candidate 5 (score 4.30)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 二、学员疑问与讨论记录 > Q1：为什么不使用 LangGraph？`
- content_fingerprint: `273b555cdc7c722e...`
- evidence_excerpt:

  ```
  **学员理解：**
  > 自定义 checkpoint 本身就是参考 LangGraph 设计思想实现的，所以迁移是"回归标准"而非"推倒重来"。当前节点按 StateGraph Node 模式设计（纯函数、输入 state 输出 state），迁移只需改工作流节点和面试流程相关的东西，评分、画像等模块零改动——Port/Adapter 分层和单一职责保障了这一点。
  
  **教师补充：**
  
  三层保障使得迁移成本极低：
  1. **设计同源**：节点本身就是按 LangGraph Node 模式设计
  2. **边已隐含**：`InterviewService` 的调用顺序天然对应 `add_edge(A, B)`
  3. **其他模块零改动**：评分、画像只通过领域对象交互，不依赖工作流框架
  
  **面试话术红线：**
  
  ```

- suggested_answer_points (verify before use):
  - 自定义 checkpoint 本身就是参考 LangGraph 设计思想实现的，所以迁移是"回归标准"而非"推倒重来"。当前节点按 StateGraph Node 模式设计（纯函数、输入 state 输出 state），迁移只需改工作流节点和面试流程相关的东西，评分、画像等模块零改动——Port/Adapter 分层和
  - 三层保障使得迁移成本极低：
  - 设计同源：节点本身就是按 LangGraph Node 模式设计

## ret-017

- question: 为什么 V1 不引入 Elasticsearch？
- declared answerability: full
- diagnostic_keywords: ['V1', 'PostgreSQL', '复杂度']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 5.63)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 为什么面试时不能回避边界？`
- content_fingerprint: `f20faf45cf065aa2...`
- evidence_excerpt:

  ```
  每条边界都需要能说出对应的生产方案：
  
  | 边界                 | 需要准备的知识                                               |
  | -------------------- | ------------------------------------------------------------ |
  | 本地 BGE Embedding   | 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界 |
  | 非 LangGraph Runtime | LangGraph 适合什么场景、当前为什么不需用、如何迁移           |
  | 基础文本解析         | OCR（扫描 PDF）、版面分析（多栏/表格）、复杂表格重建——不同格式的难点 |
  ```

- suggested_answer_points (verify before use):
  - 每条边界都需要能说出对应的生产方案：
  - 边界 — 需要准备的知识
  - 本地 BGE Embedding — 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界

### candidate 2 (score 5.63)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 的三条核心价值`
- content_fingerprint: `f490a5d69dd04ba9...`
- evidence_excerpt:

  ```
  | 价值           | 为什么                                            |
  | -------------- | ------------------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，RRF 只看排名         |
  | **双路有加成** | 两路都召回 → 两个排名都参与计算 → 天然加分        |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献，不会被粗暴截断 |
  ```

- suggested_answer_points (verify before use):
  - 价值 — 为什么
  - 量纲无关 — 不管原始分是 0.72 还是 9500，RRF 只看排名
  - 双路有加成 — 两路都召回 → 两个排名都参与计算 → 天然加分

### candidate 3 (score 5.63)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 二、学员疑问与讨论记录 > Q1：RRF 排名融合是怎么计算的，为什么要使用 RRF 融合？`
- content_fingerprint: `9ab75490bb8e64a0...`
- evidence_excerpt:

  ```
  **回答：**
  
  核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  
  RRF 不看分数只看排名，公式 `score = Σ 1/(k + rank)`（k=60）。三条核心价值：
  
  | 价值           | 为什么                                   |
  | -------------- | ---------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，只看排名    |
  | **双路有加成** | 两路都召回 → 两个排名参与计算 → 天然加分 |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献        |
  
  ```

- suggested_answer_points (verify before use):
  - 核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  - RRF 不看分数只看排名，公式 score = Σ 1/(k + rank)（k=60）。三条核心价值：
  - 价值 — 为什么

### candidate 4 (score 5.33)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 面试重点：为什么需要 ProfileUpdateEvent？`
- content_fingerprint: `7a20ce406e61aff2...`
- evidence_excerpt:

  ```
  它不是多余的日志，而是**画像副作用的审计记录**：
  - 同一 Evaluation 是否已经应用（防重复）
  - 为什么跳过更新（disputed/review_pending）
  - 更新前后掌握度如何变化
  - 使用的是哪一版层级模型
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 它不是多余的日志，而是画像副作用的审计记录：
  - 同一 Evaluation 是否已经应用（防重复）
  - 为什么跳过更新（disputed/review_pending）

### candidate 5 (score 4.97)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 一、教案正文 > 6.9 掌握度和覆盖度为什么必须分开`
- content_fingerprint: `4920eaad458263b6...`
- evidence_excerpt:

  ```
  | 概念                   | 回答什么问题                   | 示例                          |
  | ---------------------- | ------------------------------ | ----------------------------- |
  | **掌握度**（画像）     | "用户回答过的题，表现怎么样？" | RAG 掌握度 0.47               |
  | **覆盖度**（知识目录） | "知识库里的内容，被考到过吗？" | "多模态 RAG" 状态 = uncovered |
  ```

- suggested_answer_points (verify before use):
  - 概念 — 回答什么问题 — 示例
  - 掌握度（画像） — "用户回答过的题，表现怎么样？" — RAG 掌握度 0.47
  - 覆盖度（知识目录） — "知识库里的内容，被考到过吗？" — "多模态 RAG" 状态 = uncovered

## ret-018

- question: 为什么评测需要 Recall@K 和 MRR？
- declared answerability: full
- diagnostic_keywords: ['Recall', 'MRR', '评测']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 7.50)

- document_logical_name: `第 7 课：工程化专题 + 面试实战`
- heading_path: `第 7 课：工程化专题 + 面试实战 > 一、教案正文 > 7.3 企业级 RAG 演进路线 > 为什么不能一开始就拆微服务`
- content_fingerprint: `b99d9aa6fe73d1f4...`
- evidence_excerpt:

  ```
  企业化的优先级应是**权限、数据质量和评测证据**，而不是服务数量。先保持模块边界，通过接口逐步替换基础设施；只有独立扩缩容、故障隔离或团队所有权出现明确需求时再拆服务。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 企业化的优先级应是权限、数据质量和评测证据，而不是服务数量。先保持模块边界，通过接口逐步替换基础设施；只有独立扩缩容、故障隔离或团队所有权出现明确需求时再拆服务。

### candidate 2 (score 7.00)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 面试重点：为什么需要 ProfileUpdateEvent？`
- content_fingerprint: `7a20ce406e61aff2...`
- evidence_excerpt:

  ```
  它不是多余的日志，而是**画像副作用的审计记录**：
  - 同一 Evaluation 是否已经应用（防重复）
  - 为什么跳过更新（disputed/review_pending）
  - 更新前后掌握度如何变化
  - 使用的是哪一版层级模型
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 它不是多余的日志，而是画像副作用的审计记录：
  - 同一 Evaluation 是否已经应用（防重复）
  - 为什么跳过更新（disputed/review_pending）

### candidate 3 (score 7.00)

- document_logical_name: `第 7 课：工程化专题 + 面试实战`
- heading_path: `第 7 课：工程化专题 + 面试实战 > 一、教案正文 > 7.3 企业级 RAG 演进路线 > 企业化五阶段`
- content_fingerprint: `250ef769ea88222f...`
- evidence_excerpt:

  ```
  ```
  当前个人版闭环
    → ① 身份、租户、权限
         SSO/OIDC + RBAC + 检索前置 ACL + 跨租户越权测试
    → ② 数据连接器与文档治理
         对象存储、Wiki/网盘 Connector、增量同步、OCR、版面、表格
    → ③ 生产 Embedding 与检索评测
         BGE/多语言 Embedding、Reranker、标注集、Recall@K、NDCG
    → ④ 可靠队列与工作流运行时
         消息队列、独立 Worker、任务租约、死信、Trace/指标/日志
    → ⑤ 组织技能矩阵与训练平台
         岗位职级、评分人工复核、团队训练计划、聚合趋势与隐私
  ```

- suggested_answer_points (verify before use):
  - → ① 身份、租户、权限
  - SSO/OIDC + RBAC + 检索前置 ACL + 跨租户越权测试
  - → ② 数据连接器与文档治理

### candidate 4 (score 6.80)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 一、教案正文 > 6.7 复习任务：为什么需要两次验证 > 为什么不是一次高分就完成`
- content_fingerprint: `085f8db728d81e8e...`
- evidence_excerpt:

  ```
  | 一次高分的问题                   | 两次验证的价值               |
  | -------------------------------- | ---------------------------- |
  | 可能恰好出了用户熟悉的题（运气） | 连续两次才能证明"确实掌握了" |
  | 参考答案演示可能让用户照抄得高分 | 两次不同题目的高分更难作假   |
  | 一次高分直接抹掉长期错误证据     | 需要持续证明才能消除错误记录 |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 一次高分的问题 — 两次验证的价值
  - 可能恰好出了用户熟悉的题（运气） — 连续两次才能证明"确实掌握了"
  - 参考答案演示可能让用户照抄得高分 — 两次不同题目的高分更难作假

### candidate 5 (score 6.30)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.2 为什么需要两路检索`
- content_fingerprint: `90548028082cb2b1...`
- evidence_excerpt:

  ```
  | 查询类型   | 示例                             | 适合的检索           |
  | ---------- | -------------------------------- | -------------------- |
  | 语义改写   | "如何恢复中断的 Agent 流程"      | 向量检索（语义相近） |
  | 精确标识符 | `WorkflowCheckpointModel`、`RRF` | 全文检索（精确匹配） |
  
  技术资料同时包含自然语言和精确标识符，单路召回容易漏失。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 查询类型 — 示例 — 适合的检索
  - 语义改写 — "如何恢复中断的 Agent 流程" — 向量检索（语义相近）
  - 精确标识符 — WorkflowCheckpointModel、RRF — 全文检索（精确匹配）

## ret-019

- question: 知识库证据不足时 allow_model_knowledge=false 有什么效果？
- declared answerability: full
- diagnostic_keywords: ['allow_model_knowledge', '证据不足', '禁止']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 10.46)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.7 第二道防线：证据门禁`
- content_fingerprint: `6fd691f5dbdd6e40...`
- evidence_excerpt:

  ```
  ```python
  supported_candidates = self._supported_candidates(question, candidates)
  sufficient = (
      bool(supported_candidates)
      and supported_candidates[0].score >= self._min_evidence_score
  )
  
  if not sufficient and not allow_model_knowledge:
      return await self._persist(
          answer="当前知识库证据不足，我不能把模型常识伪装成资料结论。",
          citations=[],
          evidence_sufficient=False,
  ```

- suggested_answer_points (verify before use):
  - supported_candidates = self._supported_candidates(question, candidates)
  - sufficient = (
  - bool(supported_candidates)

### candidate 2 (score 7.92)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 二、学员疑问与讨论记录 > Q1：当前 RAG 是不是比较 LOW？Embedding 必须改造吗？ > Embedding 层确实基础，但工程防御层不 LOW`
- content_fingerprint: `2000a380bd1c8df2...`
- evidence_excerpt:

  ```
  Embedding 弱不等于整个 RAG 弱。当前 RAG 的工程深度体现在**检索之后**：
  
  ```
  检索（弱） → RRF 融合 → 每文档限额 → 相邻块去重 → 
  词汇化证据判断 → 分数阈值门禁 → 证据不足拒答 →
  LLM 生成 → 引用白名单校验 → 持久化诊断信息
  ```
  
  这些环节不依赖 Embedding 质量，它们是对"检索结果不可信"的防御层。恰恰因为 Embedding 弱，这套防御才更有意义——证明了系统不靠"运气好搜到对的东西"来工作。
  ```

- suggested_answer_points (verify before use):
  - Embedding 弱不等于整个 RAG 弱。当前 RAG 的工程深度体现在检索之后：
  - 检索（弱） → RRF 融合 → 每文档限额 → 相邻块去重 →
  - 词汇化证据判断 → 分数阈值门禁 → 证据不足拒答 →

### candidate 3 (score 7.54)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.9 LLM 生成层：双路径兜底`
- content_fingerprint: `7f16fc52f34567ec...`
- evidence_excerpt:

  ```
  ```python
  async def _generate_answer(self, ...):
      if self._llm is None:
          # 路径 A：确定性组合（无 LLM）
          return (self._compose_grounded_answer(...), "deterministic", "llm_not_configured", ...)
      try:
          # 路径 B：LLM 结构化生成
          output = await self._llm.generate_structured(...)
          ensure_citations_are_valid(output.citation_chunk_ids, candidates)
          if not output.evidence_suff
  ```

- suggested_answer_points (verify before use):
  - async def _generate_answer(self, ...):
  - if self._llm is None:
  - 路径 A：确定性组合（无 LLM）

### candidate 4 (score 6.92)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 二、学员疑问与讨论记录 > Q2：文档大幅重排问题，面试中怎么回答？没有企业经验会难吗？ > 面试时这样说的效果`
- content_fingerprint: `1c3aa443b014a084...`
- evidence_excerpt:

  ```
  | 层级              | 你说的                                        | 面试官听到的                             |
  | ----------------- | --------------------------------------------- | ---------------------------------------- |
  | 方案1（内容指纹） | "类似上传阶段的 Hash 去重，延伸到 Chunk 层面" | 他能举一反三，把已有能力延伸到新问题     |
  | 方案2（结构路径） | "标题路径已经在采集了，匹配逻辑从一维变二维"  | 他知道自己系统里有什么数据，不是凭空设计 |
  | 方案3（版本化）   | "企业级方案是版本化引用，历史绑定版本号"      | 他有架构视
  ```

- suggested_answer_points (verify before use):
  - 层级 — 你说的 — 面试官听到的
  - 方案1（内容指纹） — "类似上传阶段的 Hash 去重，延伸到 Chunk 层面" — 他能举一反三，把已有能力延伸到新问题
  - 方案2（结构路径） — "标题路径已经在采集了，匹配逻辑从一维变二维" — 他知道自己系统里有什么数据，不是凭空设计

### candidate 5 (score 6.00)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.5 分块策略：为什么不是固定字数切割`
- content_fingerprint: `0f90d67f1ebccba4...`
- evidence_excerpt:

  ```
  当前使用 `chunk_sections` 按**标题边界**切分，而不是按固定字数硬切：
  
  ```
  按标题边界切分（当前做法）：
    "## RRF 公式\nRRF 的基本思想是..."  →  一个完整块
    "## 引用白名单\n引用白名单的作用..."  →  另一个完整块
  
  按固定字数硬切（坏做法）：
    "## RRF 公式\nRRF 的基本思想是[切到一半]..."  →  语义断裂
    "[块2继续]..."  →  上下文丢失
  ```
  ```

- suggested_answer_points (verify before use):
  - 当前使用 chunk_sections 按标题边界切分，而不是按固定字数硬切：
  - 按标题边界切分（当前做法）：
  - "## RRF 公式\nRRF 的基本思想是..."  →  一个完整块

## ret-020

- question: 单文档占比控制想避免什么问题？
- declared answerability: full
- diagnostic_keywords: ['单文档', '占比', '多样性']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 6.92)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 一、教案正文 > 6.3 两层模型 > 分别解决什么问题`
- content_fingerprint: `5e10ae2700491fa6...`
- evidence_excerpt:

  ```
  |                  | 第一层：稳定主题                   | 第二层：动态诊断子知识点                      |
  | ---------------- | ---------------------------------- | --------------------------------------------- |
  | **粒度**         | 粗（10-20 个）                     | 细（50-100+ 个）                              |
  | **回答的问题**   | "用户 RAG 整体能力怎么样？"        | "RAG 里哪里是短板？是 RRF 融合还是引用校验？" |
  | **用途**         | 长期趋势图、下一轮选什么主题     
  ```

- suggested_answer_points (verify before use):
  - 第一层：稳定主题 — 第二层：动态诊断子知识点
  - 粒度 — 粗（10-20 个） — 细（50-100+ 个）
  - 回答的问题 — "用户 RAG 整体能力怎么样？" — "RAG 里哪里是短板？是 RRF 融合还是引用校验？"

### candidate 2 (score 6.92)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 二、学员疑问与讨论记录 > Q2：主题与子知识点分别解决什么问题？`
- content_fingerprint: `4e1c1bd94d5f0651...`
- evidence_excerpt:

  ```
  **回答：**
  
  |            | 第一层：稳定主题             | 第二层：动态诊断子知识点                      |
  | ---------- | ---------------------------- | --------------------------------------------- |
  | 回答的问题 | "用户 RAG 整体能力怎么样？"  | "RAG 里哪里是短板？是 RRF 融合还是引用校验？" |
  | 用途       | 长期趋势图、下一轮选什么主题 | 具体复习建议、错误模式诊断                    |
  | 面试官看到 | "RAG 从 0.40 → 0.47，在进步" | "薄弱点在 RRF 融合"                           |
  
  只用一层的问题：
  - 只有主题层：
  ```

- suggested_answer_points (verify before use):
  - 第一层：稳定主题 — 第二层：动态诊断子知识点
  - 回答的问题 — "用户 RAG 整体能力怎么样？" — "RAG 里哪里是短板？是 RRF 融合还是引用校验？"
  - 用途 — 长期趋势图、下一轮选什么主题 — 具体复习建议、错误模式诊断

### candidate 3 (score 4.92)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 二、学员疑问与讨论记录 > Q2：文档大幅重排问题，面试中怎么回答？没有企业经验会难吗？ > 面试时这样说的效果`
- content_fingerprint: `1c3aa443b014a084...`
- evidence_excerpt:

  ```
  | 层级              | 你说的                                        | 面试官听到的                             |
  | ----------------- | --------------------------------------------- | ---------------------------------------- |
  | 方案1（内容指纹） | "类似上传阶段的 Hash 去重，延伸到 Chunk 层面" | 他能举一反三，把已有能力延伸到新问题     |
  | 方案2（结构路径） | "标题路径已经在采集了，匹配逻辑从一维变二维"  | 他知道自己系统里有什么数据，不是凭空设计 |
  | 方案3（版本化）   | "企业级方案是版本化引用，历史绑定版本号"      | 他有架构视
  ```

- suggested_answer_points (verify before use):
  - 层级 — 你说的 — 面试官听到的
  - 方案1（内容指纹） — "类似上传阶段的 Hash 去重，延伸到 Chunk 层面" — 他能举一反三，把已有能力延伸到新问题
  - 方案2（结构路径） — "标题路径已经在采集了，匹配逻辑从一维变二维" — 他知道自己系统里有什么数据，不是凭空设计

### candidate 4 (score 4.62)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.5 检索后处理：为什么还要限额和去重 > 每文档限额（max_chunks_per_document）`
- content_fingerprint: `2f46a5152e27d796...`
- evidence_excerpt:

  ```
  不加限制：某篇 100 页文档占全部 Top-K → 来源单一。  
  加限制后：每篇最多贡献 N 个 chunk → 来源多样化。
  ```

- suggested_answer_points (verify before use):
  - 不加限制：某篇 100 页文档占全部 Top-K → 来源单一。
  - 加限制后：每篇最多贡献 N 个 chunk → 来源多样化。

### candidate 5 (score 4.31)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.7 重新索引时为什么尽量保留 Chunk ID > 边界`
- content_fingerprint: `3483eaf8f8c2dc13...`
- evidence_excerpt:

  ```
  如果文档大幅重排（段落插入/删除），相同 `chunk_index` 可能已经不是同一语义——这是真实的局限。
  
  面试时可给出递进式改进思路（详见下方疑问记录）。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 如果文档大幅重排（段落插入/删除），相同 chunk_index 可能已经不是同一语义——这是真实的局限。
  - 面试时可给出递进式改进思路（详见下方疑问记录）。

## ret-021

- question: 相邻 chunk 去重为什么有必要？
- declared answerability: full
- diagnostic_keywords: ['相邻', 'chunk', '去重']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 14.89)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.5 检索后处理：为什么还要限额和去重 > 相邻块去重`
- content_fingerprint: `3e79331b3eebdc74...`
- evidence_excerpt:

  ```
  连续相邻 chunk 内容高度重叠 → 去掉后为不同位置腾出空间。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 连续相邻 chunk 内容高度重叠 → 去掉后为不同位置腾出空间。

### candidate 2 (score 11.44)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.5 检索后处理：为什么还要限额和去重 > 每文档限额（max_chunks_per_document）`
- content_fingerprint: `2f46a5152e27d796...`
- evidence_excerpt:

  ```
  不加限制：某篇 100 页文档占全部 Top-K → 来源单一。  
  加限制后：每篇最多贡献 N 个 chunk → 来源多样化。
  ```

- suggested_answer_points (verify before use):
  - 不加限制：某篇 100 页文档占全部 Top-K → 来源单一。
  - 加限制后：每篇最多贡献 N 个 chunk → 来源多样化。

### candidate 3 (score 9.44)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.7 重新索引时为什么尽量保留 Chunk ID`
- content_fingerprint: `d107530c0aeba4b2...`
- evidence_excerpt:

  ```
  ```python
  existing_chunks = {
      chunk.chunk_index: chunk
      for chunk in existing_chunk_rows
  }
  
  for draft, vector in zip(drafts, vectors, strict=True):
      chunk = existing_chunks.pop(draft.chunk_index, None)
      if chunk is None:
          session.add(KnowledgeChunkModel(...))     # 新块 → 新建
      else:
          chunk.content = draft.content              # 已有块 → 更新内容
  ```

- suggested_answer_points (verify before use):
  - existing_chunks = {
  - chunk.chunk_index: chunk
  - for chunk in existing_chunk_rows

### candidate 4 (score 9.44)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.7 重新索引时为什么尽量保留 Chunk ID > 为什么这么做`
- content_fingerprint: `405fb34d5cc05abf...`
- evidence_excerpt:

  ```
  历史面试题和评分可能引用了旧的 Chunk ID。如果每次重建都删除全部 Chunk：
  - 历史评估的 `reference_chunk_ids` 会变成悬空引用
  - 历史报告中的引用来源会丢失
  
  当前方案优先按 `chunk_index` 更新原记录，从而尽量保持引用稳定。
  ```

- suggested_answer_points (verify before use):
  - 历史面试题和评分可能引用了旧的 Chunk ID。如果每次重建都删除全部 Chunk：
  - 历史评估的 reference_chunk_ids 会变成悬空引用
  - 历史报告中的引用来源会丢失

### candidate 5 (score 9.44)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.7 重新索引时为什么尽量保留 Chunk ID > 边界`
- content_fingerprint: `3483eaf8f8c2dc13...`
- evidence_excerpt:

  ```
  如果文档大幅重排（段落插入/删除），相同 `chunk_index` 可能已经不是同一语义——这是真实的局限。
  
  面试时可给出递进式改进思路（详见下方疑问记录）。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 如果文档大幅重排（段落插入/删除），相同 chunk_index 可能已经不是同一语义——这是真实的局限。
  - 面试时可给出递进式改进思路（详见下方疑问记录）。

## ret-022

- question: PostgreSQL pgvector 在这个项目中有什么好处？
- declared answerability: full
- diagnostic_keywords: ['PostgreSQL', 'pgvector', '业务数据']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 8.67)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 1.2 六层架构（先建立系统地图）`
- content_fingerprint: `9d2290297c59a0e0...`
- evidence_excerpt:

  ```
  ```
  ┌──────────────────────────────────────────────┐
  │  交互层    React 前端 (知识库/问答/面试/画像)     │
  ├──────────────────────────────────────────────┤
  │  接口层    FastAPI Router (7个路由)              │
  │           chat / knowledge / interviews /      │
  │           evaluations / profiles / demo        │
  ├──────────────────────────────────────────────┤
  │  应用层    Service (编排中心)                    │
  │           An
  ```

- suggested_answer_points (verify before use):
  - ┌──────────────────────────────────────────────┐
  - │  交互层    React 前端 (知识库/问答/面试/画像)     │
  - ├──────────────────────────────────────────────┤

### candidate 2 (score 8.00)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 1.1 一句话讲清这个项目是什么`
- content_fingerprint: `a97eee5f117d7075...`
- evidence_excerpt:

  ```
  > **AgentMentor 是一个面向个人学习者的 AI 面试训练系统。** 它把学习资料变成可检索证据，通过 RAG 支撑问答和面试出题，再用可信评分更新能力画像和复习任务，形成"学习→训练→评分→画像→下一轮"的闭环。整套系统可在 16GB 普通开发机上通过 Docker Compose 运行。
  ```

- suggested_answer_points (verify before use):
  - AgentMentor 是一个面向个人学习者的 AI 面试训练系统。 它把学习资料变成可检索证据，通过 RAG 支撑问答和面试出题，再用可信评分更新能力画像和复习任务，形成"学习→训练→评分→画像→下一轮"的闭环。整套系统可在 16GB 普通开发机上通过 Docker Compose 运行。

### candidate 3 (score 7.33)

- document_logical_name: `第 7 课：工程化专题 + 面试实战`
- heading_path: `第 7 课：工程化专题 + 面试实战 > 一、教案正文 > 7.7 学完整个项目后应该形成的认知`
- content_fingerprint: `303a6e239f475bd6...`
- evidence_excerpt:

  ```
  > AgentMentor 的核心价值不是"用大模型生成三道题"，而是把学习资料、可溯源检索、人机工作流、可信评分和长期画像连接成一个受约束的训练闭环。系统通过应用层规则限制 LLM 的权力，通过 checkpoint 和幂等保证流程状态，通过两层画像控制长期记忆粒度，再通过增量知识目录区分"回答得怎么样"和"资料是否考到"，形成补缺与查漏两类训练信号；并在 16GB 本地约束下选择 PostgreSQL、本地 BGE-small-zh 和模块化单体。它已经是一个真实可运行的个人学习系统，但还不是企业级终态；当前已补同知识库最近历史题目冷却，全量语义题库去重、复杂文档、生产检索评测、租户权限和可靠异步任务是明确的演进方向。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - AgentMentor 的核心价值不是"用大模型生成三道题"，而是把学习资料、可溯源检索、人机工作流、可信评分和长期画像连接成一个受约束的训练闭环。系统通过应用层规则限制 LLM 的权力，通过 checkpoint 和幂等保证流程状态，通过两层画像控制长期记忆粒度，再通过增量知识目录区分"回答得怎么样"和"资料是否考到

### candidate 4 (score 6.67)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.1 先说结论`
- content_fingerprint: `fb1ad6a0cea0ebdc...`
- evidence_excerpt:

  ```
  一条完整的知识入库链路：
  
  ```
  用户上传文件
    → 后端二次校验文件类型
    → SHA-256 内容去重（同内容拒绝，同名不同内容形成新版本）
    → 解析（Markdown/TXT/PDF/DOCX → 纯文本+结构信息）
    → 分块（按标题边界切分，带 overlap 防语义断裂）
    → Embedding（文本→向量，当前默认 BGE-small-zh，测试/无模型环境可降级到 development）
    → 双重索引（pgvector 向量 + PostgreSQL tsvector 全文）
    → 增量目录同步（提取标题路径为 KnowledgeCatalogPoint）
    → 状态变为 READY
  ```

- suggested_answer_points (verify before use):
  - 一条完整的知识入库链路：
  - → 后端二次校验文件类型
  - → SHA-256 内容去重（同内容拒绝，同名不同内容形成新版本）

### candidate 5 (score 5.33)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > 具体计算示例`
- content_fingerprint: `38e56212b02e77e9...`
- evidence_excerpt:

  ```
  假设搜"RRF 融合"，两路返回：
  
  ```
             向量召回排名    全文召回排名
  A（RRF段落）  第1名         第3名
  B（pgvector） 第2名         未召回（∞）
  C（全文检索） 未召回（∞）     第1名
  D（混合检索） 第3名         第2名
  ```
  
  计算：
  ```
  ```

- suggested_answer_points (verify before use):
  - 假设搜"RRF 融合"，两路返回：
  - 向量召回排名    全文召回排名
  - A（RRF段落）  第1名         第3名

## ret-023

- question: 回答与引用关系为什么要持久化？
- declared answerability: full
- diagnostic_keywords: ['持久化', '引用', '追溯']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 10.22)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.8 第三道防线：引用白名单 > 引用白名单不能做什么`
- content_fingerprint: `c5f36d17cbfd078b...`
- evidence_excerpt:

  ```
  | ❌ 不能                           | 为什么                   |
  | -------------------------------- | ------------------------ |
  | 证明片段完整支持答案中所有 claim | 模型可能断章取义         |
  | 证明文档本身一定正确             | 来源合法性 ≠ 内容正确性  |
  | 证明检索没有漏掉关键证据         | 没召回的东西白名单管不了 |
  | 证明模型没有曲解原文             | 模型可能歪曲 chunk 含义  |
  
  准确表述：**"引用来源合法性校验"**，不是 **"完全消除幻觉"**。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ❌ 不能 — 为什么
  - 证明片段完整支持答案中所有 claim — 模型可能断章取义
  - 证明文档本身一定正确 — 来源合法性 ≠ 内容正确性

### candidate 2 (score 9.61)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.8 第三道防线：引用白名单 > 引用白名单能做什么`
- content_fingerprint: `9fb3ac5e9a05d041...`
- evidence_excerpt:

  ```
  - 防止 LLM 编造不存在或不属于本轮上下文的 Chunk ID
  - 保证用户点开引用链接时能看到对应内容
  ```

- suggested_answer_points (verify before use):
  - 防止 LLM 编造不存在或不属于本轮上下文的 Chunk ID
  - 保证用户点开引用链接时能看到对应内容

### candidate 3 (score 9.22)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 二、学员疑问与讨论记录 > Q1：RRF 排名融合是怎么计算的，为什么要使用 RRF 融合？`
- content_fingerprint: `9ab75490bb8e64a0...`
- evidence_excerpt:

  ```
  **回答：**
  
  核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  
  RRF 不看分数只看排名，公式 `score = Σ 1/(k + rank)`（k=60）。三条核心价值：
  
  | 价值           | 为什么                                   |
  | -------------- | ---------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，只看排名    |
  | **双路有加成** | 两路都召回 → 两个排名参与计算 → 天然加分 |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献        |
  
  ```

- suggested_answer_points (verify before use):
  - 核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  - RRF 不看分数只看排名，公式 score = Σ 1/(k + rank)（k=60）。三条核心价值：
  - 价值 — 为什么

### candidate 4 (score 7.31)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.5 分块策略：为什么不是固定字数切割`
- content_fingerprint: `0f90d67f1ebccba4...`
- evidence_excerpt:

  ```
  当前使用 `chunk_sections` 按**标题边界**切分，而不是按固定字数硬切：
  
  ```
  按标题边界切分（当前做法）：
    "## RRF 公式\nRRF 的基本思想是..."  →  一个完整块
    "## 引用白名单\n引用白名单的作用..."  →  另一个完整块
  
  按固定字数硬切（坏做法）：
    "## RRF 公式\nRRF 的基本思想是[切到一半]..."  →  语义断裂
    "[块2继续]..."  →  上下文丢失
  ```
  ```

- suggested_answer_points (verify before use):
  - 当前使用 chunk_sections 按标题边界切分，而不是按固定字数硬切：
  - 按标题边界切分（当前做法）：
  - "## RRF 公式\nRRF 的基本思想是..."  →  一个完整块

### candidate 5 (score 7.31)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.7 重新索引时为什么尽量保留 Chunk ID > 为什么这么做`
- content_fingerprint: `405fb34d5cc05abf...`
- evidence_excerpt:

  ```
  历史面试题和评分可能引用了旧的 Chunk ID。如果每次重建都删除全部 Chunk：
  - 历史评估的 `reference_chunk_ids` 会变成悬空引用
  - 历史报告中的引用来源会丢失
  
  当前方案优先按 `chunk_index` 更新原记录，从而尽量保持引用稳定。
  ```

- suggested_answer_points (verify before use):
  - 历史面试题和评分可能引用了旧的 Chunk ID。如果每次重建都删除全部 Chunk：
  - 历史评估的 reference_chunk_ids 会变成悬空引用
  - 历史报告中的引用来源会丢失

## ret-024

- question: 面试助手为什么要先做证据化问答？
- declared answerability: full
- diagnostic_keywords: ['面试助手', '证据化', '学习']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 7.30)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 一、教案正文 > 6.5 为什么高分后画像不会立刻满分——渐进更新 > 为什么设计成这样`
- content_fingerprint: `859e3676c1473f08...`
- evidence_excerpt:

  ```
  | 设计目的                        | 防止的问题                             |
  | ------------------------------- | -------------------------------------- |
  | 一次高分不能覆盖全部历史        | 参考答案演示、偶然命题、运气好         |
  | 学习率受 confidence_weight 影响 | 低置信评分影响力弱                     |
  | 学习率受 difficulty 影响        | 简单题答对不加分太多，难题答对加分更多 |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 设计目的 — 防止的问题
  - 一次高分不能覆盖全部历史 — 参考答案演示、偶然命题、运气好
  - 学习率受 confidence_weight 影响 — 低置信评分影响力弱

### candidate 2 (score 7.00)

- document_logical_name: `第 6 课：两层画像与复习闭环`
- heading_path: `第 6 课：两层画像与复习闭环 > 一、教案正文 > 6.5 为什么高分后画像不会立刻满分——渐进更新 > 公式解读`
- content_fingerprint: `20bfa159e09117ea...`
- evidence_excerpt:

  ```
  ```
  新掌握度 = 旧掌握度 + (本次得分 - 旧掌握度) × 学习率
  
  学习率 = min(0.35, 0.18 × confidence_weight × difficulty_factor)
  ```
  ```

- suggested_answer_points (verify before use):
  - 新掌握度 = 旧掌握度 + (本次得分 - 旧掌握度) × 学习率
  - 学习率 = min(0.35, 0.18 × confidence_weight × difficulty_factor)

### candidate 3 (score 6.87)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 为什么面试时不能回避边界？`
- content_fingerprint: `f20faf45cf065aa2...`
- evidence_excerpt:

  ```
  每条边界都需要能说出对应的生产方案：
  
  | 边界                 | 需要准备的知识                                               |
  | -------------------- | ------------------------------------------------------------ |
  | 本地 BGE Embedding   | 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界 |
  | 非 LangGraph Runtime | LangGraph 适合什么场景、当前为什么不需用、如何迁移           |
  | 基础文本解析         | OCR（扫描 PDF）、版面分析（多栏/表格）、复杂表格重建——不同格式的难点 |
  ```

- suggested_answer_points (verify before use):
  - 每条边界都需要能说出对应的生产方案：
  - 边界 — 需要准备的知识
  - 本地 BGE Embedding — 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界

### candidate 4 (score 6.87)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 二、学员疑问与讨论记录 > Q1：RRF 排名融合是怎么计算的，为什么要使用 RRF 融合？`
- content_fingerprint: `9ab75490bb8e64a0...`
- evidence_excerpt:

  ```
  **回答：**
  
  核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  
  RRF 不看分数只看排名，公式 `score = Σ 1/(k + rank)`（k=60）。三条核心价值：
  
  | 价值           | 为什么                                   |
  | -------------- | ---------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，只看排名    |
  | **双路有加成** | 两路都召回 → 两个排名参与计算 → 天然加分 |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献        |
  
  ```

- suggested_answer_points (verify before use):
  - 核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。
  - RRF 不看分数只看排名，公式 score = Σ 1/(k + rank)（k=60）。三条核心价值：
  - 价值 — 为什么

### candidate 5 (score 6.57)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 面试重点：为什么需要 ProfileUpdateEvent？`
- content_fingerprint: `7a20ce406e61aff2...`
- evidence_excerpt:

  ```
  它不是多余的日志，而是**画像副作用的审计记录**：
  - 同一 Evaluation 是否已经应用（防重复）
  - 为什么跳过更新（disputed/review_pending）
  - 更新前后掌握度如何变化
  - 使用的是哪一版层级模型
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 它不是多余的日志，而是画像副作用的审计记录：
  - 同一 Evaluation 是否已经应用（防重复）
  - 为什么跳过更新（disputed/review_pending）

## ret-025

- question: 为什么测试环境不能误读真实 API Key？
- declared answerability: full
- diagnostic_keywords: ['测试环境', 'API Key', '安全']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 6.87)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 为什么面试时不能回避边界？`
- content_fingerprint: `f20faf45cf065aa2...`
- evidence_excerpt:

  ```
  每条边界都需要能说出对应的生产方案：
  
  | 边界                 | 需要准备的知识                                               |
  | -------------------- | ------------------------------------------------------------ |
  | 本地 BGE Embedding   | 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界 |
  | 非 LangGraph Runtime | LangGraph 适合什么场景、当前为什么不需用、如何迁移           |
  | 基础文本解析         | OCR（扫描 PDF）、版面分析（多栏/表格）、复杂表格重建——不同格式的难点 |
  ```

- suggested_answer_points (verify before use):
  - 每条边界都需要能说出对应的生产方案：
  - 边界 — 需要准备的知识
  - 本地 BGE Embedding — 云 Embedding、Reranker、向量版本治理和企业级检索服务；知道本地小模型与生产治理的边界

### candidate 2 (score 6.87)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 的三条核心价值`
- content_fingerprint: `f490a5d69dd04ba9...`
- evidence_excerpt:

  ```
  | 价值           | 为什么                                            |
  | -------------- | ------------------------------------------------- |
  | **量纲无关**   | 不管原始分是 0.72 还是 9500，RRF 只看排名         |
  | **双路有加成** | 两路都召回 → 两个排名都参与计算 → 天然加分        |
  | **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献，不会被粗暴截断 |
  ```

- suggested_answer_points (verify before use):
  - 价值 — 为什么
  - 量纲无关 — 不管原始分是 0.72 还是 9500，RRF 只看排名
  - 双路有加成 — 两路都召回 → 两个排名都参与计算 → 天然加分

### candidate 3 (score 6.30)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 解决了什么，没解决什么`
- content_fingerprint: `f82633b37d14f9ca...`
- evidence_excerpt:

  ```
  | ✅ 解决了                             | ❌ 没解决                                 |
  | ------------------------------------ | ---------------------------------------- |
  | 两种异构分数不可比的问题             | 如果两路都没召回正确答案，RRF 也救不了   |
  | 排名融合的稳定性（不依赖原始分尺度） | 检索质量的上限仍取决于两路各自的召回能力 |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ✅ 解决了 — ❌ 没解决
  - 两种异构分数不可比的问题 — 如果两路都没召回正确答案，RRF 也救不了
  - 排名融合的稳定性（不依赖原始分尺度） — 检索质量的上限仍取决于两路各自的召回能力

### candidate 4 (score 6.00)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > RRF 公式`
- content_fingerprint: `c0163e197002f710...`
- evidence_excerpt:

  ```
  ```python
  def reciprocal_rank_fusion(ranked_lists, *, rrf_k=60):
      scores = {}
      for ranked in ranked_lists:
          for rank, chunk_id in enumerate(ranked, start=1):
              scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
      return scores
  ```
  
  公式：`score = Σ 1/(k + rank)`
  ```

- suggested_answer_points (verify before use):
  - def reciprocal_rank_fusion(ranked_lists, *, rrf_k=60):
  - scores = {}
  - for ranked in ranked_lists:

### candidate 5 (score 6.00)

- document_logical_name: `第 3 课：混合检索与可信 RAG 回答`
- heading_path: `第 3 课：混合检索与可信 RAG 回答 > 一、教案正文 > 3.3 RRF 融合：为什么不能直接加分数 > 具体计算示例`
- content_fingerprint: `38e56212b02e77e9...`
- evidence_excerpt:

  ```
  假设搜"RRF 融合"，两路返回：
  
  ```
             向量召回排名    全文召回排名
  A（RRF段落）  第1名         第3名
  B（pgvector） 第2名         未召回（∞）
  C（全文检索） 未召回（∞）     第1名
  D（混合检索） 第3名         第2名
  ```
  
  计算：
  ```
  ```

- suggested_answer_points (verify before use):
  - 假设搜"RRF 融合"，两路返回：
  - 向量召回排名    全文召回排名
  - A（RRF段落）  第1名         第3名

## ret-026

- question: 如何用 RAG 支撑之后的模拟面试出题？
- declared answerability: full
- diagnostic_keywords: ['RAG', '出题', '证据']
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 12.85)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 1.4 核心闭环（整套系统如何串起来）`
- content_fingerprint: `17b6053fe5695d05...`
- evidence_excerpt:

  ```
  ```
  学习资料成为证据
      ↓
  证据支撑两条消费路径：
      ├── 路径A：RAG问答（用户提问→检索→证据判断→LLM回答→引用校验）
      └── 路径B：模拟面试（训练主题→检索出题→用户回答→可信评分→画像更新）
      ↓
  评分沉淀为能力和错误
      ↓
  错误生成复习任务
      ↓
  画像推荐下一轮训练主题（当前是"画像推荐+用户确认+主题注入"，非全自主Agent）
  ```

- suggested_answer_points (verify before use):
  - 学习资料成为证据
  - 证据支撑两条消费路径：
  - ├── 路径A：RAG问答（用户提问→检索→证据判断→LLM回答→引用校验）

### candidate 2 (score 12.31)

- document_logical_name: `第 4 课：可恢复模拟面试工作流`
- heading_path: `第 4 课：可恢复模拟面试工作流 > 二、学员疑问与讨论记录 > Q2：刷新恢复的具体交互是怎样的？`
- content_fingerprint: `9721ea017ed46490...`
- evidence_excerpt:

  ```
  **回答：**
  
  前端用 localStorage 存 interview_id → 刷新后 GET /interviews/{id} → 服务端根据持久化的 InterviewSession、InterviewQuestion、UserAnswer 返回完整状态（当前第几题、题目内容、已提交答案）→ 前端重新渲染。checkpoint 主要提供流程轨迹和排障证据，不是唯一恢复来源。
  
  所有状态都在服务端数据库，localStorage 只存一个 ID，避免浏览器状态与服务端不一致。
  
  ---
  ```

- suggested_answer_points (verify before use):
  - 前端用 localStorage 存 interview_id → 刷新后 GET /interviews/{id} → 服务端根据持久化的 InterviewSession、InterviewQuestion、UserAnswer 返回完整状态（当前第几题、题目内容、已提交答案）→ 前端重新渲染。checkpoint
  - 所有状态都在服务端数据库，localStorage 只存一个 ID，避免浏览器状态与服务端不一致。

### candidate 3 (score 10.84)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 两条消费路径的关键区别`
- content_fingerprint: `033ee93ae1432e5a...`
- evidence_excerpt:

  ```
  |             | RAG 问答                       | 模拟面试                            |
  | ----------- | ------------------------------ | ----------------------------------- |
  | **目的**    | 回答"学习资料能否回答当前问题" | 回答"用户是否真正掌握资料内容"      |
  | **输出**    | 带引用的答案                   | 题目+参考答案+Rubric→评分→画像      |
  | **LLM角色** | 基于证据生成答案               | 出题+评分（但应用层控制评分可信度） |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - RAG 问答 — 模拟面试
  - 目的 — 回答"学习资料能否回答当前问题" — 回答"用户是否真正掌握资料内容"
  - 输出 — 带引用的答案 — 题目+参考答案+Rubric→评分→画像

### candidate 4 (score 10.62)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 二、学员疑问与讨论记录 > Q1：当前 RAG 是不是比较 LOW？Embedding 必须改造吗？ > Embedding 层确实基础，但工程防御层不 LOW`
- content_fingerprint: `2000a380bd1c8df2...`
- evidence_excerpt:

  ```
  Embedding 弱不等于整个 RAG 弱。当前 RAG 的工程深度体现在**检索之后**：
  
  ```
  检索（弱） → RRF 融合 → 每文档限额 → 相邻块去重 → 
  词汇化证据判断 → 分数阈值门禁 → 证据不足拒答 →
  LLM 生成 → 引用白名单校验 → 持久化诊断信息
  ```
  
  这些环节不依赖 Embedding 质量，它们是对"检索结果不可信"的防御层。恰恰因为 Embedding 弱，这套防御才更有意义——证明了系统不靠"运气好搜到对的东西"来工作。
  ```

- suggested_answer_points (verify before use):
  - Embedding 弱不等于整个 RAG 弱。当前 RAG 的工程深度体现在检索之后：
  - 检索（弱） → RRF 融合 → 每文档限额 → 相邻块去重 →
  - 词汇化证据判断 → 分数阈值门禁 → 证据不足拒答 →

### candidate 5 (score 10.54)

- document_logical_name: `第 1 课：项目全景与架构地图`
- heading_path: `第 1 课：项目全景与架构地图 > 一、教案正文 > 1.1 一句话讲清这个项目是什么`
- content_fingerprint: `a97eee5f117d7075...`
- evidence_excerpt:

  ```
  > **AgentMentor 是一个面向个人学习者的 AI 面试训练系统。** 它把学习资料变成可检索证据，通过 RAG 支撑问答和面试出题，再用可信评分更新能力画像和复习任务，形成"学习→训练→评分→画像→下一轮"的闭环。整套系统可在 16GB 普通开发机上通过 Docker Compose 运行。
  ```

- suggested_answer_points (verify before use):
  - AgentMentor 是一个面向个人学习者的 AI 面试训练系统。 它把学习资料变成可检索证据，通过 RAG 支撑问答和面试出题，再用可信评分更新能力画像和复习任务，形成"学习→训练→评分→画像→下一轮"的闭环。整套系统可在 16GB 普通开发机上通过 Docker Compose 运行。


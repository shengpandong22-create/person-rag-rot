# Candidate Evidence Packages — HUMAN REVIEW REQUIRED

- source_dataset: `evals\datasets\retrieval_validation_v1.jsonl`
- packages: 2
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

## va-pt-001

- question: PDF 文档的解析限制和 OCR 支持情况分别是什么？
- declared answerability: partial
- diagnostic_keywords: []
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 5.01)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.4 解析阶段：四种格式怎么处理 > 已实现 vs 未实现`
- content_fingerprint: `41b66037eb2fa753...`
- evidence_excerpt:

  ```
  | ✅ 已实现                                 | ❌ 未实现          |
  | ---------------------------------------- | ----------------- |
  | Markdown（标题、段落、代码、列表、表格） | OCR（扫描件 PDF） |
  | TXT（纯文本）                            | 多栏阅读顺序恢复  |
  | 文本型 PDF（直接提取文字层）             | 复杂表格结构重建  |
  | DOCX（Word 文档）                        | 图片/图表理解     |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ✅ 已实现 — ❌ 未实现
  - Markdown（标题、段落、代码、列表、表格） — OCR（扫描件 PDF）
  - TXT（纯文本） — 多栏阅读顺序恢复

### candidate 2 (score 4.77)

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

### candidate 3 (score 4.54)

- document_logical_name: `第 4 课：可恢复模拟面试工作流`
- heading_path: `第 4 课：可恢复模拟面试工作流 > 一、教案正文 > 4.4 Checkpoint：它是什么，能做什么，不能做什么 > Checkpoint 不能做什么`
- content_fingerprint: `dda7621e1c629344...`
- evidence_excerpt:

  ```
  | ❌ 不能                     | 为什么                             |
  | -------------------------- | ---------------------------------- |
  | 从任意 Python 语句自动续跑 | 记录的是业务节点，不是代码执行位置 |
  | 分布式任务租约和调度       | 没有 Worker 调度机制               |
  | 节点级自动重试和补偿       | 没有通用的失败重试框架             |
  | 时间旅行                   | LangGraph 有，当前没有             |
  ```

- suggested_answer_points (verify before use):
  - ❌ 不能 — 为什么
  - 从任意 Python 语句自动续跑 — 记录的是业务节点，不是代码执行位置
  - 分布式任务租约和调度 — 没有 Worker 调度机制

### candidate 4 (score 4.54)

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

## va-pt-002

- question: 系统如何控制单文档占比，以及在多大规模下验证过？
- declared answerability: partial
- diagnostic_keywords: []
- note: candidates are model suggestions; select and verify before setting label_origin=human

### candidate 1 (score 6.00)

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

### candidate 2 (score 4.70)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.8 增量知识目录：新文档如何进入查漏体系 > 关键规则`
- content_fingerprint: `4d4238a75bd866b9...`
- evidence_excerpt:

  ```
  | 规则                                 | 目的                               |
  | ------------------------------------ | ---------------------------------- |
  | 有二级标题时，一级标题只作为主题容器 | 避免"RAG"同时作为主题和具体考点    |
  | 标题规范化生成稳定 `point_key`       | 重新索引不重复创建节点             |
  | 新文档只增加 `uncovered` 知识点      | 不修改已有画像分数                 |
  | 文档归档时删除有效来源关系           | 失去活动来源的知识点不参与覆盖统计 |
  
  因此，重新导入资料不是"清空画像重新训练"，而是给已有知识边界增加新
  ```

- suggested_answer_points (verify before use):
  - 有二级标题时，一级标题只作为主题容器 — 避免"RAG"同时作为主题和具体考点
  - 标题规范化生成稳定 point_key — 重新索引不重复创建节点
  - 新文档只增加 uncovered 知识点 — 不修改已有画像分数

### candidate 3 (score 4.50)

- document_logical_name: `第 2 课：知识入库链路——文档如何变成可检索证据`
- heading_path: `第 2 课：知识入库链路——文档如何变成可检索证据 > 一、教案正文 > 2.4 解析阶段：四种格式怎么处理 > 已实现 vs 未实现`
- content_fingerprint: `41b66037eb2fa753...`
- evidence_excerpt:

  ```
  | ✅ 已实现                                 | ❌ 未实现          |
  | ---------------------------------------- | ----------------- |
  | Markdown（标题、段落、代码、列表、表格） | OCR（扫描件 PDF） |
  | TXT（纯文本）                            | 多栏阅读顺序恢复  |
  | 文本型 PDF（直接提取文字层）             | 复杂表格结构重建  |
  | DOCX（Word 文档）                        | 图片/图表理解     |
  
  ---
  ```

- suggested_answer_points (verify before use):
  - ✅ 已实现 — ❌ 未实现
  - Markdown（标题、段落、代码、列表、表格） — OCR（扫描件 PDF）
  - TXT（纯文本） — 多栏阅读顺序恢复

### candidate 4 (score 4.50)

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


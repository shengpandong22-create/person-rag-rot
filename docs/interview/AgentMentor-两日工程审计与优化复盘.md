# AgentMentor 两日工程审计与优化复盘

> 定位：这不是普通开发日志，而是一份面试可讲的工程复盘材料。  
> 目标：说明项目不是“功能堆出来就结束”，而是经历了真实运行、审计发现、最小改动优化和回归验证。  
> 适用场景：面试官追问“你这个项目有什么真实问题？你怎么发现？怎么改？怎么证明改好了？”

---

## 1. 一句话总结

这两天的优化重点不是继续堆新功能，而是把 AgentMentor 从“流程能跑通”推进到“训练质量、工程边界和面试表达都能被验证”。

我围绕三个问题做审计：

1. **系统是否真的稳定可运行**：Docker、依赖、前端构建、后端测试是否一致；
2. **训练是否真的有效**：题目是否重复、知识点是否覆盖、评分是否有区分度；
3. **项目表达是否诚实**：文档是否把未来规划说成已实现，是否存在旧口径。

最终形成的结果是：项目不仅能演示完整闭环，还能拿出评估报告、运行态证据、审计脚本和回归测试，说明每次优化不是主观感觉，而是有证据支撑。

---

## 2. 为什么这部分是面试加分项

很多个人 AI 项目停留在“我接了一个模型 API，然后做了一个页面”。这类项目面试时很容易被问倒：

- 你怎么知道 RAG 回答没编？
- 你怎么知道评分不是随机的？
- 你怎么保证画像不是前端随便显示？
- 你怎么发现题目是否重复？
- 你怎么证明这次优化没有破坏旧功能？

这两天的审计和优化，正好把这些问题变成了可讲的工程故事：

> 我先用真实多轮面试验证系统闭环，再用评估脚本拆解检索、评分、出题和画像质量。发现问题后，没有大改架构，而是用最小改动补上证据门禁、评分区分度、历史题冷却、运行态观测和文档口径校正。每次改动后都跑 ruff、pyright、pytest、前端 build 和必要的 Docker 验收。

这个表达能体现三种能力：

- **工程判断力**：知道什么时候该大改，什么时候该小修；
- **质量意识**：不是只看页面能不能点，而是看指标和边界；
- **面试可信度**：敢讲项目限制，也能讲清楚为什么这样取舍。

---

## 3. 审计方法：我是怎么一步步发现问题的

### 3.1 先做真实闭环压测

在 BGE、画像隔离、知识库切换等能力完成后，使用真实 API 和真实数据库跑多轮模拟面试。

验证对象包括：

- 知识库能否正常入库；
- BGE embedding + pgvector 能否正常检索；
- 面试是否能创建、启动、答题、完成；
- 报告是否能生成；
- 画像是否跟随知识库隔离；
- 复习任务是否能随评分推进；
- 多轮历史和趋势是否保留。

这一步的价值是：先证明系统不是“单接口可用”，而是“业务闭环可用”。

代码/脚本路线：

- `scripts/run_knowledge_base_interview_audit.py`
- `src/agent_mentor/application/interview_service.py`
- `src/agent_mentor/application/evaluation_service.py`
- `src/agent_mentor/application/profile_service.py`
- `docs/evaluations/results/`

### 3.2 再拆成质量维度审计

闭环跑通后，我没有继续做大功能，而是把训练质量拆成几个可验证维度：

| 审计维度 | 核心问题 | 验证方式 |
| --- | --- | --- |
| RAG 边界 | 问资料外问题时会不会乱答 | 构造负例问题，检查 `evidence_guard` |
| 检索质量 | 正确 chunk 是否被召回 | Retrieval Eval Runner 输出 Recall@K / MRR |
| 评分区分度 | 低/中/高质量答案能否拉开分 | Scoring Eval Runner 输出 MAE / Pearson |
| 出题多样性 | 多轮是否反复问相似题 | 审计题目文本相似度和角度分布 |
| 画像可信度 | 高分是否能渐进更新画像 | 多轮面试后检查 profile / review task |
| 运行态一致性 | 本地代码和 Docker 服务是否一致 | `/health/runtime` 暴露版本和启动时间 |
| 文档可信度 | 面试材料是否有过度承诺 | grep 扫描企业级、生产级、旧 BGE 口径 |

这一步的价值是：把“感觉不好”变成“可以定位的问题”。

### 3.3 最后按最小改动修复

这两天没有做大架构重构，而是遵循一个原则：

> 不改变主流程、不引入重组件、不重写模块，只补足关键质量短板和证据链。

比如：

- RAG 边界不靠 prompt 祈祷，而是在 `AnswerService` 增强证据判断；
- 出题重复不建复杂题库系统，而是先加最近历史冷却窗口；
- 评分可信不靠主观评价，而是补人工答案集和评分 Eval；
- 文档可信不重写所有材料，而是修正会影响面试表达的旧口径。

---

## 4. 关键优化复盘

### 4.1 RAG 知识边界修复

#### 问题是怎么发现的

审计时发现一个危险场景：如果用户问“唐朝开元年间的盐税制度如何影响 RAG 系统设计”这类资料外问题，检索可能因为包含 “RAG / 系统设计” 等通用词而召回项目文档。

如果系统只看表面相关性，就可能把无关资料当作证据，让 LLM 生成看似合理但不来自知识库的回答。

#### 为什么这个问题重要

RAG 项目最怕的不是“不回答”，而是“把模型常识伪装成知识库证据”。如果这个边界不清，面试官会质疑整个 RAG 可信度。

#### 如何调整

在 `AnswerService` 中把证据判断抽成 `assess_evidence()`，并增强词法支持逻辑：

- 过滤过于泛化的证据词；
- 对中英混合、跨领域问题增加更严格的支持判断；
- 让 Eval Runner 和真实回答链路使用同一套证据判断；
- 证据不足时返回 `evidence_guard`，不生成伪引用答案。

代码路线：

- `src/agent_mentor/application/answer_service.py`
- `tests/unit/test_retrieval.py`
- `evals/runners/retrieval_runner.py`

#### 如何验收

真实请求负例问题：

```text
唐朝开元年间的具体盐税制度如何影响 RAG 系统设计？
```

期望结果：

```json
{
  "evidence_sufficient": false,
  "generation_mode": "evidence_guard",
  "fallback_reason": "insufficient_evidence",
  "citations": []
}
```

后续 Retrieval Eval 中：

```text
negative_rejection_accuracy = 1.0
```

#### 面试表达

> 我不只做了“能回答”的 RAG，还专门验证“什么时候不该回答”。因为在面试训练场景里，资料外答案会污染用户判断。我把证据判断从回答链路里抽出来，让真实 API 和 Eval Runner 共用同一套逻辑，并用负例问题验证系统能进入 evidence_guard，而不是强行编造引用。

---

### 4.2 Retrieval Eval Runner 增强

#### 问题是怎么发现的

早期检索效果只能靠肉眼体验：“感觉召回还行”。但面试官如果追问“你怎么证明 BGE 或 chunk 优化真的有效”，主观体验不够。

#### 如何调整

增强检索评估报告，记录：

- 数据集 hash；
- 知识库指纹；
- 文档数量、ready 文档数量、chunk 数量、目录知识点数量；
- embedding provider、model、dimension；
- retrieval 参数；
- Recall@1 / Recall@3 / Recall@6；
- MRR；
- 证据充分率；
- 负例拒答准确率；
- 失败样本和关键词覆盖诊断。

代码路线：

- `evals/runners/retrieval_runner.py`
- `evals/reports/retrieval_current/`
- `docs/evaluations/training-quality-audit-20260902.md`

#### 当前结果

最新一次检索评估摘要：

| 指标 | 结果 |
| --- | ---: |
| Recall@1 | 0.5 |
| Recall@3 | 0.6538 |
| Recall@6 | 0.7308 |
| MRR | 0.5865 |
| evidence_sufficient_accuracy | 0.7667 |
| negative_rejection_accuracy | 1.0 |

#### 面试表达

> 我没有把检索优化停留在“看起来不错”。我补了 Retrieval Eval Runner，把知识库指纹、数据集 hash、模型配置和检索参数都写入报告。这样后续换 BGE、调 chunk、调 top_k，都能用同一套数据对比，而不是凭感觉说效果提升。

---

### 4.3 Scoring Eval Runner 与评分区分度

#### 问题是怎么发现的

50 轮真实面试主要使用参考答案提交，能证明流程稳定，但不能证明评分器有区分度。因为参考答案天然高质量，系统打高分是合理的，却不能说明低质量答案会被打低。

#### 如何调整

新增人工答案集：

- 同一题构造 low / mid / high 三档回答；
- 给每条样例标注人工预期分；
- 分别跑 fallback 评分和 LLM 评分；
- 输出 MAE、Pearson correlation、Reviewer routing accuracy、band order accuracy。

代码路线：

- `evals/datasets/evaluation_discrimination_v1.jsonl`
- `evals/runners/scoring_runner.py`
- `evals/metrics.py`
- `tests/unit/test_eval_metrics.py`

#### 当前结果

| 指标 | fallback baseline | LLM 评分 |
| --- | ---: | ---: |
| MAE | 7.1667 | 1.6667 |
| Pearson correlation | 0.8735 | 0.9802 |
| Reviewer routing accuracy | 0.4167 | 1.0 |
| Band order accuracy | 1.0 | 1.0 |

#### 审计结论

- fallback 评分能大致排序，但明显偏保守；
- LLM 评分更接近人工标注，能拉开低、中、高答案；
- 当前样本只有 12 条，后续仍需扩大评测集，不能过度宣称“评分完全客观”。

#### 面试表达

> 我发现只用参考答案跑面试，会让评分结果天然偏高，所以我补了一组人工答案集，专门验证评分区分度。结果显示 fallback 能排序但偏保守，DeepSeek 评分在 12 条样例上 MAE 为 1.6667，Pearson 为 0.9802，说明评分趋势和人工判断较一致。但我也会强调样本规模还小，不能说评分完全客观。

---

### 4.4 画像更新与知识库隔离

#### 问题是怎么发现的

真实使用时发现：用户切换知识库后，如果画像仍然是全局共享，就会出现 Agent 知识库的训练结果影响 Java 知识库画像，反之亦然。

这会直接破坏项目核心卖点：画像驱动的长期训练闭环。

#### 如何调整

采用两层模型：

- **稳定主题作为主画像**：如 RAG、LangGraph、Java 后端；
- **动态子知识点作为诊断证据**：如引用白名单、缓存穿透、工作流恢复；
- **画像跟随知识库隔离**：不同知识库拥有不同画像；
- **可信评分渐进更新**：不是一次高分直接覆盖；
- **连续高分推进复习任务**：避免偶然高分关闭任务。

代码路线：

- `src/agent_mentor/application/profile_service.py`
- `src/agent_mentor/domain/profile.py`
- `src/agent_mentor/domain/profile_taxonomy.py`
- `src/agent_mentor/api/profiles.py`
- `frontend/src/components/ProfilePanel.jsx`

#### 面试表达

> 画像可以理解成一种简版长期 Memory，但它不是自由文本记忆，而是有结构、有来源、有置信门禁的任务型记忆。它只消费可信评分，并且跟随知识库隔离，避免不同学习资料之间相互污染。

---

### 4.5 查漏机制：覆盖度和掌握度分离

#### 问题是怎么发现的

用户可能连续几轮都拿高分，但这不代表知识库里的所有知识点都被考过。高分只能说明“已考内容掌握得不错”，不能说明“未考内容也会”。

#### 如何调整

把画像拆成两类信号：

- **掌握度**：回答过的问题答得怎么样；
- **覆盖度**：知识库里的知识点是否被考到过。

新增文档后，系统不会因为新增未覆盖知识点就降低已有画像分，而是把新知识点标记为 `uncovered`，进入查漏推荐。

代码路线：

- `src/agent_mentor/application/coverage_catalog.py`
- `src/agent_mentor/application/profile_service.py`
- `src/agent_mentor/application/interview_service.py`
- `docs/evaluations/incremental-document-coverage-acceptance-20260802.md`

#### 面试表达

> 我后来发现补缺和查漏不是一回事。补缺是“用户哪里答错了”，查漏是“知识库里还有什么没考过”。所以我把掌握度和覆盖度分开：新增资料只增加 uncovered，不直接降低已有掌握度；面试中会保底抽一题覆盖盲区。

---

### 4.6 题目多样性：角度轮换与历史题冷却

#### 问题是怎么发现的

50 轮真实训练后发现：系统流程没有中断，但同主题下题面可能反复围绕“RAG 是什么、如何落地、如何保证可靠性”展开。题目不完全相同，但用户体感会觉得重复。

这说明“流程稳定”不等于“训练质量高”。

#### 第一阶段调整：考察角度轮换

新增 `QuestionAngle`，让每题不只由 topic 和 question_type 决定，还由考察角度驱动：

- 概念边界；
- 架构取舍；
- 异常与降级；
- 生产化与观测；
- 对比辨析；
- 质量评估。

题目 rubric 中记录 `question_angle`，审计脚本统计角度分布。

#### 第二阶段调整：同知识库最近历史题目冷却

继续审计后发现，角度轮换只能减少单轮重复，跨多轮仍可能遇到近期相似问法。因此增加最近历史题冷却：

- 查询同一知识库最近 12 道历史题；
- 传入出题 prompt；
- 要求模型避开近期核心问法；
- 与本轮题一起进入相似度保护；
- 触发 fallback 时记录 `similar_to_recent_knowledge_base_question`；
- 在 `rubric.generation.recent_question_cooldown_count` 中记录冷却数量。

代码路线：

- `src/agent_mentor/application/interview_service.py`
- `scripts/run_knowledge_base_interview_audit.py`
- `tests/unit/test_interview_service.py`
- `tests/unit/test_interview_audit_runner.py`

#### 真实验收

2 轮 Agent 面试审计：

| 指标 | 结果 |
| --- | ---: |
| 完成轮数 | 2 / 2 |
| 总题数 | 6 |
| failures | 0 |
| with_cooldown_trace | 6 |
| active_cooldown_questions | 6 |
| max_recent_question_cooldown_count | 12 |
| near_duplicate_count | 0 |
| deterministic_similarity_fallback | 1 |

其中 1 题触发：

```text
similar_to_recent_knowledge_base_question
```

这说明历史冷却不是摆设，而是真的拦截过近期相似题。

#### 当前边界

这不是完整题库级语义去重：

- 没有把历史题向量化；
- 没有建立题库相似度索引；
- 不能保证全历史永不重复。

但作为最小改造，它已经显著改善连续训练体验。

#### 面试表达

> 我做 50 轮后发现，系统稳定不代表训练有效，题目可能在同主题里打转。我的第一步是加考察角度轮换，第二步是加同知识库最近 12 道历史题冷却。它不是完整题库语义去重，但已经能低成本降低近期重复，并且冷却数量和 fallback 原因都写进 trace，可以被审计。

---

### 4.7 前端状态恢复与运行态观测

#### 问题是怎么发现的

用户刷新页面后，如果前端显示“本地降级、没有知识库”，即使后端实际正常，面试官也会认为系统没有跑通。

另外，曾经出现过代码已改，但 Docker API 容器仍是旧进程，导致审计结果看起来和代码不一致。

#### 如何调整

- 前端刷新后自动恢复最近有资料的知识库；
- 知识库选择和本机画像绑定；
- `/health/runtime` 暴露运行态信息；
- 前端展示 LLM、Embedding、API 版本、启动时间等运行证据；
- 审计脚本把 runtime 快照写入结果文件。

代码路线：

- `src/agent_mentor/api/health.py`
- `src/agent_mentor/main.py`
- `frontend/src/main.jsx`
- `frontend/src/components/KnowledgeBaseControls.jsx`
- `frontend/src/components/AppLayout.jsx`
- `scripts/run_knowledge_base_interview_audit.py`

#### 面试表达

> 我把运行态信息显式展示出来，是因为 AI 项目很容易出现“代码变了但服务没重启”的误判。通过 `/health/runtime` 和前端状态区，可以直接看到当前是否启用了 DeepSeek、是否使用 BGE、API 什么时候启动，从而减少演示不确定性。

---

### 4.8 前端评分解释优化

#### 问题是怎么发现的

早期评分报告虽然有总分和维度分，但逐题解释容易模板化，用户看完仍然不知道为什么这题扣分。

#### 如何调整

前端 `buildQuestionAnalysis()` 从单一模板改成组合式解释：

- 最低维度；
- 已覆盖要点；
- 主要遗漏；
- 不准确表述；
- 低置信提示；
- 下一步补强建议。

代码路线：

- `frontend/src/utils/report.js`
- `frontend/src/components/EvaluationPanel.jsx`

#### 面试表达

> 评分不是只给一个数字。我把后端的 `covered_points`、`missing_points`、`incorrect_claims`、confidence 和四维分数组合成前端逐题解析，让用户知道“为什么扣分、下一步怎么补”。这比单纯展示模型 feedback 更可控。

---

### 4.9 文档和面试材料口径校正

#### 问题是怎么发现的

项目迭代很快，部分文档还停留在旧版本：

- 仍说 Embedding 是特征哈希开发基线；
- 仍说 BGE 是后续增强；
- 仍说评分 Eval Runner 未完成；
- 对 checkpoint 和自动恢复的边界说法不够准确；
- 部分地方容易把当前项目说成企业级终态。

#### 如何调整

统一口径：

- 当前默认 BGE-small-zh，保留 development fallback；
- BGE 已落地，但不是企业级向量服务；
- checkpoint 支持刷新恢复和流程追踪，但不是通用工作流引擎；
- 评分 Eval Runner 已落地，但样本规模仍需扩大；
- 当前是个人学习训练系统，不是企业级 RAG 平台。

文档路线：

- `docs/interview/AgentMentor-V2-项目掌握与源码走读手册.md`
- `docs/interview/agentmentor-v2-interview-qa.md`
- `docs/interview/AgentMentor 正常面试视角回答.md`
- `docs/learning/`
- `docs/operations/project-handoff-v2.md`

#### 面试表达

> 这部分我专门做过文档审计，因为项目迭代快，文档很容易留下旧口径。我把“已实现”“降级能力”“后续演进”重新分清楚，避免面试时把未来规划说成当前能力。对个人项目来说，诚实表达边界反而是加分项。

---

## 5. 这两天形成的主要提交

| 提交 | 主题 | 价值 |
| --- | --- | --- |
| `c0602de` | 对齐 RAG 边界评估口径 | 资料外问题能正确拒答 |
| `597371f` | 补齐检索评估运行态元数据 | Eval 报告可追溯 |
| `683bee0` | 增强评分区分度报告追溯 | 评分质量可量化 |
| `180ab04` | 绑定检索报告知识库指纹 | 避免评估对象混乱 |
| `10202d9` | 补充检索失败关键词覆盖诊断 | 能解释召回失败原因 |
| `430e3c7` | 沉淀检索失败覆盖诊断 | 形成审计文档证据 |
| `0d98cd2` | 校验 Docker 依赖与项目依赖同步 | 防止容器依赖漂移 |
| `10c5eb7` | 同步 BGE 落地后的面试口径 | 文档与代码一致 |
| `7e7abc1` | 增加历史题冷却与审计证据 | 改善题目多样性 |
| `eb50e9f` | 优化逐题评分解释文案 | 前端反馈更可理解 |

---

## 6. 回归与验收方式

这两天每一批改动后都尽量按四层验收：

### 6.1 静态质量

```bash
ruff check .
pyright
```

目的：

- 保证代码风格和类型检查不过线；
- 避免小修引入隐藏错误。

### 6.2 单元测试

```bash
pytest -q
```

当前最近结果：

```text
99 passed, 1 skipped
```

跳过项：

```text
tests/integration/test_learning_loop.py
```

原因：没有配置独立 PostgreSQL 集成测试库。

### 6.3 前端构建

```bash
npm.cmd --prefix frontend run build
```

目的：

- 防止 React 页面改完打不开；
- 防止 JSX、import、状态变量错误。

### 6.4 Docker 运行态验收

```bash
docker compose build api
docker compose up -d api
docker compose build frontend
docker compose up -d frontend
```

并检查：

```bash
http://localhost:3000/ 返回 200
/health/ready 返回 ok
/health/runtime 返回 LLM 和 Embedding 状态
```

### 6.5 真实业务审计

```bash
python scripts/run_knowledge_base_interview_audit.py agent \
  --base-url http://localhost:8000 \
  --rounds 2 \
  --output docs/evaluations/results/agent-cooldown-audit-20260903.json
```

目的：

- 不只相信单测；
- 通过真实 API、真实数据库、真实 LLM 流程验证业务链路。

---

## 7. 面试时可以怎么讲这段经历

### 7.1 30 秒版本

> 项目跑通后，我没有马上继续堆功能，而是做了一轮工程审计。先用真实多轮面试验证闭环，再拆成 RAG 边界、检索召回、评分区分度、题目多样性、画像隔离和运行态一致性几个维度。审计发现题目有重复风险、评分需要人工答案集验证、RAG 对资料外问题要更严格、文档口径也有旧版本残留。后续我用最小改动补了 evidence guard、Eval Runner、历史题冷却、运行态观测和逐题评分解释，并通过 ruff、pyright、pytest、前端 build、Docker 和真实审计脚本回归。

### 7.2 90 秒版本

> AgentMentor 一开始已经能跑完整闭环：资料入库、RAG、面试、评分、画像和复习计划。但我后来意识到“能跑通”不等于“训练质量可信”。所以我做了两类审计：一类是工程稳定性，比如 Docker 运行态、依赖同步、前端刷新恢复；另一类是训练质量，比如 RAG 是否会资料外乱答、评分是否能区分低中高答案、题目是否重复、画像是否跟随知识库隔离。
>
> 审计过程中发现几个问题：RAG 可能被通用关键词误召回，评分用参考答案跑会天然偏高，多轮面试可能出现相似题，文档里还有旧版本口径。我的处理不是大拆架构，而是小步修：在 `AnswerService` 加证据门禁并和 Eval 共用；新增 retrieval/scoring eval runner；在出题阶段加入考察角度轮换和同知识库最近历史题冷却；前端逐题解释从模板话改成最低维度、覆盖点、缺失点、错误论断组合；最后把文档改成当前真实能力边界。
>
> 这些改动后，我能拿出具体证据，比如负例拒答准确率达到 1.0，DeepSeek 评分在人工答案集上的 MAE 是 1.6667、Pearson 是 0.9802，历史题冷却 2 轮真实审计中 6 题全部生效且近似重复为 0。这个过程体现的是：我不是只会调模型 API，而是在把 AI 系统当作一个需要评估、观测和回归的工程系统做。

### 7.3 如果面试官追问“这是不是过度包装”

可以回答：

> 我不会说它是企业级终态，也不会说完全解决了 RAG 和 Agent 的所有问题。这个项目的价值在于：它是一个个人开发机可运行的完整学习闭环，并且对关键风险做了可验证的约束。比如证据不足拒答、引用白名单、评分区分度、画像门禁、幂等提交、运行态观测，这些都是 AI 应用落地时真正会遇到的问题。边界我也写清楚了：没有企业 ACL、没有 OCR 版面模型、没有全量语义题库去重、没有通用工作流引擎。

---

## 8. 面试官可能追问与回答要点

### Q1：你是怎么发现题目重复问题的？

不是靠单次体验，而是跑多轮真实面试后观察到同主题题目虽然文字不同，但核心问法相似。后来我把题目文本、question_angle、generation_mode 和相似度摘要写入审计报告，用脚本统计近似重复对。

### Q2：为什么不直接做完整题库语义去重？

因为那需要新增题目 embedding、历史题索引、相似度阈值治理和迁移成本。当前阶段用最近 12 道历史题冷却，改动小、风险低、能解决近期重复体验问题。完整题库语义去重是后续增强。

### Q3：RAG 边界为什么比回答能力更重要？

面试训练场景里，错误答案会误导用户复习方向。系统宁可告诉用户“资料不足”，也不能把模型常识包装成知识库结论。否则画像和评分都会被污染。

### Q4：评分区分度怎么证明？

我构造了低、中、高三档人工答案集，跑 scoring eval。fallback 排序正确但偏保守，LLM 评分 MAE 为 1.6667、Pearson 为 0.9802，说明和人工判断趋势一致。但样本还小，后续要扩大评测集。

### Q5：画像为什么不是直接等于最近一次分数？

因为一次高分可能来自题目简单、参考答案演示或偶然发挥。画像用渐进更新，并区分主题掌握度和知识点覆盖度；低置信、争议评分不会污染画像。

### Q6：你怎么保证优化没有破坏旧功能？

每次改动后跑 ruff、pyright、pytest、前端 build；涉及运行态的改动会重建 Docker，并用真实 API 跑面试审计。最近一次结果是 99 passed、1 skipped，前端构建通过，Docker 页面返回 200。

### Q7：为什么要做文档口径审计？

项目迭代快，文档容易留下旧口径。比如 BGE 已落地后，旧文档还说 Embedding 是特征哈希开发基线，面试时会自相矛盾。文档口径审计能保证简历、手册、QA 和代码一致。

---

## 9. 当前仍然诚实保留的边界

这两天优化后，项目质量提升明显，但仍不能夸大：

- 没有企业级租户、RBAC/ABAC 和文档 ACL；
- 没有 OCR、复杂表格和版面模型；
- 没有全量历史题库语义去重索引；
- 没有通用工作流引擎和任务租约；
- 评分 Eval 样本规模还小；
- 检索 Recall@K 仍有提升空间；
- API 层独立集成测试数据库还可以补强。

面试中建议用这句话收束：

> 我把当前版本定位为个人学习训练系统，而不是企业级 RAG 平台。它的优势是闭环完整、边界清晰、能本地复现，并且我能拿出审计和回归证据说明每次优化为什么做、怎么做、效果如何。企业化能力我不会夸大，会按权限、复杂文档、可靠任务、评测平台和可观测性逐步演进。

---

## 10. 最终沉淀

这两天真正有价值的不是多写了几段代码，而是形成了一套可复用的工程优化方法：

```text
真实运行
  → 暴露问题
  → 拆成可验证维度
  → 优先小改动修复
  → 补测试和审计脚本
  → Docker/前端/后端回归
  → 文档和面试口径同步
```

这也是 AgentMentor 作为简历项目最值得讲的地方：

> 它不是一个一次性 demo，而是一个经历过真实使用反馈、质量审计、指标验证和持续收敛的 AI 工程项目。


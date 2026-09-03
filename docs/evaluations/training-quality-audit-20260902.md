# AgentMentor 训练质量可信改进记录（2026-09-02）

> 目标：把项目从“流程能跑通”推进到“训练质量可解释、可观测、可回归”。  
> 约束：不做大架构重构，优先采用最小代码改动和可量化验收。

## 1. 背景

前一轮 50 次真实模拟面试已经证明系统具备完整闭环：

- 能创建知识库并完成文档入库；
- 能通过 BGE embedding + pgvector 检索资料；
- 能生成面试题、提交答案、生成报告；
- 能基于可信评分更新能力画像和复习任务；
- 能保存报告历史和趋势。

但 50 轮审计也暴露出一个新的阶段性问题：系统“不容易中断”，不等于“训练一定有效”。如果题目长期围绕相似问法打转，用户画像虽然会更新，但训练覆盖度和诊断价值都会下降。

因此，本轮改造重点从稳定性转向训练质量。

## 2. 发散审计发现的问题

### 2.1 P1：题目语义重复风险

表现：

- 同一个主题下，题目文本可能不同，但核心问法接近；
- RAG 主题容易反复问“概念、落地、可靠性”；
- 用户连续训练时会感觉题目在重复。

原因：

- 原有出题主要由主题、题型、检索片段、覆盖盲区驱动；
- 缺少“本题考察角度”这一独立维度；
- 大模型在相同主题和相似资料片段下，容易生成近似问题。

处理：

- 已在 `InterviewService` 中加入 `QuestionAngle`；
- 题目按面试 ID + 题号轮换考察角度；
- prompt 明确要求题目体现指定角度；
- 检索 query 加入角度关键词；
- rubric 记录 `question_angle`，便于后续审计。

代码路线：

- `src/agent_mentor/application/interview_service.py`
- `tests/unit/test_interview_service.py`
- `tests/unit/test_interview_workflow.py`

### 2.2 P1：题目质量缺少可量化审计指标

表现：

- 改造前只能人工翻看题目判断“是否更丰富”；
- 50 轮审计有题目、报告、画像数据，但缺少题目质量摘要；
- 不能快速回答“题目是否覆盖不同角度”“是否出现相似题”。

处理：

- 审计脚本新增 `question_angle_summary`；
- 审计脚本新增 `question_generation_summary`；
- 审计脚本新增 `question_similarity_summary`；
- 单测覆盖统计逻辑。

代码路线：

- `scripts/run_knowledge_base_interview_audit.py`
- `tests/unit/test_interview_audit_runner.py`

### 2.3 P1：相似题模板替换缺少生成元数据

表现：

- 当 LLM 生成题和本场已出题太相似时，系统会替换成确定性模板；
- 旧版本只保存替换后的题目，看不出它是 LLM 正常生成还是相似题兜底；
- 面试官追问“你如何定位出题质量问题”时，证据不够强。

处理：

- `InterviewQuestionOutput` 增加：
  - `generation_mode`
  - `fallback_reason`
- `rubric.generation` 保存：
  - mode；
  - fallback_reason；
  - prompt_version。

代码路线：

- `src/agent_mentor/application/interview_service.py`
- `tests/unit/test_interview_service.py`

### 2.4 P2：评分区分度仍需人工答案集验证

表现：

- 50 轮审计使用参考答案提交，分数整体偏高；
- 这能证明流程稳定，但不能证明系统能区分低质量、中等质量、高质量回答；
- 如果面试官追问评分可信度，仅靠参考答案跑通不够。

建议下一步：

- 准备低分、中分、高分三档人工答案；
- 用 Eval Runner 输出 MAE、相关性、复核命中率；
- 对比 LLM 评分与预期分数。

状态：待做。

### 2.5 P1：知识点覆盖仍需更长期的查漏机制

表现：

- 当前已有未覆盖知识点优先出题；
- 但新增文档后，知识点目录变大，仍需要观察哪些点长期未覆盖；
- 只看“薄弱项补缺”不够，还要看“未知点查漏”。

处理：

- 审计脚本输出 covered / uncovered / stale 知识点比例；
- 审计脚本记录训练前后的覆盖快照；
- 审计脚本输出本轮新增触达的知识点、剩余未覆盖知识点和可信覆盖率；
- 默认知识库 ID 不可用时，审计脚本会自动选择当前有文档的知识库，避免清库后误报。

状态：已补充通用审计能力，后续可继续把覆盖趋势展示到前端。

### 2.6 P1：运行态服务版本容易滞后

表现：

- 本次第一次跑 3 轮角度审计时，结果中 `question_angle_summary` 为空；
- 不是代码问题，而是 Docker API 容器仍是 47 小时前的旧进程；
- 重建并重启 API 后，角度统计正常。

处理：

- `/health/runtime` 增加 `app_version`；
- `/health/runtime` 增加 `started_at`；
- 应用启动时在 `app.state` 写入版本和启动时间。

代码路线：

- `src/agent_mentor/main.py`
- `src/agent_mentor/api/health.py`
- `tests/unit/test_health.py`

后续可继续让前端系统状态区展示该信息，审计脚本也可以把 runtime 元数据写入结果文件。

补充处理：

- `scripts/run_knowledge_base_interview_audit.py` 会在审计开始时请求 `/health/runtime`；
- 审计 JSON 顶层写入 `runtime`，用于记录本次验收对应的模型模式、embedding 配置、API 版本和启动时间；
- 后续如果出现“本地测试结果和代码不一致”，可以先检查 runtime 快照，确认是否连到了旧容器。

## 3. 本轮已落地改造

### 3.1 题目角度轮换

新增考察角度：

| 角度 | 目的 |
| --- | --- |
| 概念边界 | 检查定义、边界、易混淆概念 |
| 架构取舍 | 检查组件职责、数据流、替代方案 |
| 异常与降级 | 检查失败场景、重试、幂等、风险控制 |
| 生产化与观测 | 检查日志、指标、Trace、评估集 |
| 对比辨析 | 检查相似方案差异和选择理由 |
| 质量评估 | 检查指标设计、评测方法和质量判断 |

设计上没有新增数据库字段，而是复用 `rubric` JSON 保存元数据，避免大迁移。

### 3.2 审计脚本增强

审计结果新增三个摘要：

```json
{
  "question_angle_summary": {
    "total_questions": 9,
    "with_question_angle": 9,
    "missing_question_angle": 0,
    "distribution": {}
  },
  "question_generation_summary": {
    "total_questions": 9,
    "with_generation": 9,
    "missing_generation": 0,
    "mode_distribution": {},
    "fallback_reasons": {}
  },
  "question_similarity_summary": {
    "total_questions": 9,
    "near_duplicate_count": 0,
    "near_duplicate_pairs": []
  }
}
```

这让“训练质量”可以被脚本统计，而不是靠主观感受。

## 4. 运行态验收结果

在重建并重启 API 容器后，补跑 3 轮真实面试审计：

- 审计结果：`docs/evaluations/results/agent-angle-audit-20260902.json`
- 完成轮数：3 / 3
- 失败轮数：0
- 总题数：9
- 带 `question_angle`：9
- 缺失 `question_angle`：0

角度分布：

| 角度 | 题数 |
| --- | ---: |
| 概念边界 | 2 |
| 架构取舍 | 2 |
| 异常与降级 | 1 |
| 生产化与观测 | 1 |
| 对比辨析 | 1 |
| 质量评估 | 2 |

## 5. 回归结果

本轮代码回归：

- `ruff check`：通过；
- `pyright`：0 errors；
- `pytest`：79 passed，1 skipped。

补充运行态元数据后，相关 health 测试：

- `tests/unit/test_health.py`：3 passed。

跳过项：

- `tests/integration/test_learning_loop.py`
- 原因：未配置独立 PostgreSQL 集成测试库。

## 6. 面试表达口径

可以这样讲：

> 项目一开始我重点验证的是流程闭环：资料入库、RAG、面试、评分、画像更新都能跑通。后来我做了 50 轮真实模拟面试，发现流程稳定不代表训练质量足够好，题目存在语义重复风险。于是我没有大改架构，而是在出题服务里引入“考察角度轮换”，把题目从单纯主题驱动升级成“主题 + 检索片段 + 覆盖盲区 + 考察角度”驱动。同时我把角度和生成模式写入 rubric，并改造审计脚本统计角度分布、生成模式和近似重复题。这样训练质量就能被回归验证，而不是只靠肉眼判断。

## 7. 下一批建议

优先级从高到低：

1. 增加低/中/高三档人工答案集，验证评分区分度；
2. `/health/runtime` 暴露 API 启动时间和代码版本，减少旧容器误判；
3. 审计脚本增加知识点 covered / uncovered / stale 分布；
4. 前端展示题目角度和生成模式，让用户知道这题在考什么；
5. 多知识库再跑一次隔离验收，确认画像不串库。

## 8. 第 3 批训练质量修复：评分区分度人工答案集

### 8.1 发现的问题

此前 50 轮真实面试主要使用每题参考答案提交，适合验证工程闭环，但不适合证明评分器能区分真实用户答案质量。因为参考答案天然高质量，评分结果偏高是合理的，但它不能回答这些问题：

- 用户答得很差时，系统是否会明显低分？
- 用户答得一般时，系统是否能给中档分，而不是粗暴打成低分？
- 高质量答案是否能稳定拿到高分？
- 低质量答案是否会进入复核路由？

### 8.2 最小改造方案

新增评分区分度数据集：

- 文件：`evals/datasets/evaluation_discrimination_v1.jsonl`
- 规模：12 条
- 结构：4 组题，每组 low / mid / high 三档人工答案
- 覆盖主题：
  - RAG 知识边界；
  - LangGraph / 工作流恢复；
  - 可信评分；
  - 能力画像。

同时增强评分 Eval 指标：

- `band_order_accuracy`：低/中/高三档预测均分是否满足 `low < mid < high`，且 high-low 有足够间隔；
- `predicted_average_by_band`：各档预测均分；
- `human_average_by_band`：各档人工均分。

代码路线：

- `evals/metrics.py`
- `evals/runners/scoring_runner.py`
- `tests/unit/test_eval_metrics.py`
- `evals/datasets/evaluation_discrimination_v1.jsonl`

### 8.3 本地 baseline 结果

使用本地确定性 fallback 评分运行：

```bash
python -m evals.run scoring \
  --scoring-dataset evals/datasets/evaluation_discrimination_v1.jsonl \
  --output-dir evals/reports/discrimination_baseline
```

结果：

| 指标 | 结果 |
| --- | ---: |
| total | 12 |
| MAE | 7.1667 |
| Pearson correlation | 0.8735 |
| Reviewer routing accuracy | 0.4167 |
| Band order accuracy | 1.0 |

分档均分：

| 档位 | 人工均分 | fallback 预测均分 |
| --- | ---: | ---: |
| low | 6.0 | 2.25 |
| mid | 12.0 | 2.5 |
| high | 19.5 | 11.25 |

### 8.4 审计结论

本地 fallback 评分具备方向性：低、中、高三档整体排序是对的。但它明显偏保守，尤其会把中档答案压得接近低档，导致 MAE 较高、复核路由偏激进。

这个结论很重要：fallback 适合作为无 Key 或 LLM 失败时的保底机制，不适合作为“评分质量可信”的主要证据。真正的评分区分度验收需要继续跑 LLM 评分版本。

### 8.5 外部 LLM 评分验收边界

LLM 评分 Eval 会把 `evaluation_discrimination_v1.jsonl` 中的题目和人工答案样例发送给 DeepSeek/OpenAI-compatible 服务。由于这份数据集包含新生成的完整答案样例，不等同于此前授权的“学习文档检索片段”，因此需要单独明确授权后再运行：

```bash
python -m evals.run scoring \
  --scoring-dataset evals/datasets/evaluation_discrimination_v1.jsonl \
  --output-dir evals/reports/discrimination_llm \
  --use-llm-scoring
```

用户已在 2026-09-02 明确授权后，执行 LLM 版评分区分度验收。

结果文件：

- `evals/reports/discrimination_llm/scoring_eval.json`
- `evals/reports/discrimination_llm/scoring_eval.md`

LLM 评分结果：

| 指标 | fallback baseline | LLM 评分 |
| --- | ---: | ---: |
| MAE | 7.1667 | 2.0 |
| Pearson correlation | 0.8735 | 0.9671 |
| Reviewer routing accuracy | 0.4167 | 0.6667 |
| Band order accuracy | 1.0 | 1.0 |

分档均分对比：

| 档位 | 人工均分 | fallback 预测均分 | LLM 预测均分 |
| --- | ---: | ---: | ---: |
| low | 6.0 | 2.25 | 4.0 |
| mid | 12.0 | 2.5 | 10.0 |
| high | 19.5 | 11.25 | 18.0 |

结论：

- LLM 评分能明显拉开低、中、高三档；
- MAE 从 7.1667 降到 2.0，说明 LLM 评分比本地 fallback 更接近人工标注；
- Pearson correlation 达到 0.9671，说明评分趋势与人工判断高度一致；
- `band_order_accuracy = 1.0`，说明分档顺序正确；
- Reviewer routing accuracy 仍只有 0.6667，主要原因是中档答案虽然方向正确，但内容较简略，系统会保守进入 `used_review`。

这说明当前 LLM 评分链路已经具备较好的区分度，但复核路由策略偏保守。后续可以把“中档简略但无明显错误”的答案从强复核调整为“轻提示/低权重更新”，减少不必要的复核。

### 8.6 面试表达价值

可以这样讲：

> 我没有只用参考答案跑通流程，因为那会让评分结果天然偏高。为了验证评分器是否真的有区分度，我构造了同题低、中、高三档人工答案集，并扩展 Eval Runner 统计 MAE、相关性、复核命中率和分档排序。第一版 baseline 暴露出本地 fallback 评分偏保守的问题，这也证明这个评估不是摆设，而是能发现系统缺陷。后续使用真实 LLM 评分时，就可以对比 fallback 和 LLM 的区分度差异。

补充 LLM 验收后，可以进一步补充：

> DeepSeek 评分版在 12 条人工标注样例上，MAE 为 2.0，Pearson 相关性为 0.9671，并且低/中/高三档排序正确。这个结果说明 LLM 评分不是只会给参考答案高分，而是能对不同质量回答做出接近人工预期的区分。同时我们也发现复核路由偏保守，中档答案经常进入复核，这是下一步可以优化的点。

## 9. 第 4 批训练质量修复：复核路由降噪

### 9.1 发现的问题

LLM 评分区分度验收中，低/中/高三档分数已经能拉开，但 `Reviewer routing accuracy` 只有 0.6667。明细显示，4 条中档答案全部被送入 `used_review`。

这不是评分分数本身的问题，而是复核路由偏保守：

- 中档答案方向正确，但缺少细节；
- LLM 会把 `missing_detail` 这类训练建议写入 `review_reasons`；
- 旧规则直接接受模型输出的 `review_reasons`，导致“缺细节”也触发强复核。

### 9.2 优化原则

复核应该处理“可信性风险”，不是处理所有“训练建议”。

因此规则调整为：

- 低置信、事实冲突、引用非法、维度冲突、严重质量缺口：进入强复核；
- 缺少细节、需要更深入、表达可优化：保留在反馈和扣分中，但不触发强复核；
- 低分答案即使模型置信度高，只要存在严重质量缺口，仍会进入复核。

### 9.3 代码路线

- `src/agent_mentor/domain/evaluation.py`
  - 新增 `HARD_MODEL_REVIEW_REASONS`；
  - `review_reasons_for()` 只接收硬风险类模型原因；
  - 对 `total <= 8` 且正确性较低或缺失点较多的答案追加 `severe_quality_gap`。
- `tests/unit/test_evaluation.py`
  - 增加“中档缺细节不强复核”测试；
  - 增加“严重低质答案仍进入复核”测试。
- `evals/runners/scoring_runner.py`
  - 报告明细补充 `review_reasons`，方便定位路由原因。

### 9.4 修复后 LLM Eval 结果

重新运行：

```bash
python -m evals.run scoring \
  --scoring-dataset evals/datasets/evaluation_discrimination_v1.jsonl \
  --output-dir evals/reports/discrimination_llm \
  --use-llm-scoring
```

结果对比：

| 指标 | 修复前 | 修复后 |
| --- | ---: | ---: |
| MAE | 2.0 | 1.6667 |
| Pearson correlation | 0.9671 | 0.9691 |
| Reviewer routing accuracy | 0.6667 | 1.0 |
| Band order accuracy | 1.0 | 1.0 |

修复后表现：

- 4 条 low 答案仍全部进入复核；
- 4 条 mid 答案不再因为“缺细节”误触发强复核；
- 4 条 high 答案正常通过；
- 评分分档仍保持正确。

### 9.5 面试表达价值

可以这样讲：

> 我们用人工低中高答案集发现了一个很具体的问题：LLM 评分分数是准的，但复核路由过于敏感，中档答案会因为 missing_detail 被送入 reviewer。于是我把 review reason 分成硬风险和训练建议：只有低置信、事实冲突、引用非法、维度冲突、严重质量缺口才触发强复核；缺细节则通过扣分和反馈体现。修复后 Reviewer routing accuracy 从 0.6667 提升到 1.0，同时低分答案仍能被拦住。

## 10. 第 5 批训练质量修复：知识点覆盖 / 查漏审计

### 10.1 发现的问题

前面的优化主要解决“题目是否重复”“评分是否有区分度”“画像是否被可信评分驱动”。但从训练质量角度看，还缺少一个关键问题：

> 系统是否知道哪些知识点根本还没有考过？

如果只盯着低分项，系统会变成“补缺”工具；但真正的长期训练还需要“查漏”。尤其是新增文档后，知识点目录会变大，用户可能连续练熟悉主题，但大量新知识点仍处于未覆盖状态。

### 10.2 最小改造方案

本轮没有改核心业务逻辑，而是增强通用审计脚本，让现有 `/coverage` 能进入验收报告。

新增审计摘要：

- `coverage_summary_before`：训练前知识点覆盖快照；
- `coverage_summary_after`：训练后知识点覆盖快照；
- `coverage_progress_summary`：本轮训练带来的覆盖变化；
- 每轮 `coverage_after`：记录该轮结束后的可信覆盖率。

覆盖指标解释：

| 指标 | 含义 |
| --- | --- |
| `attempt_rate` | 已经被题目触达过的知识点比例，代表“查漏触达面”。 |
| `trusted_coverage_rate` | 已有可信评分沉淀的知识点比例，代表“可信画像覆盖面”。 |
| `top_uncovered_points` | 仍未被考过的高优先级知识点。 |
| `weak_or_insufficient_points` | 已触达但证据不足、仍需补强的知识点。 |
| `newly_attempted_points` | 本轮面试新触达的知识点。 |
| `newly_verified_points` | 本轮面试新达到可信验证状态的知识点。 |

额外修复：

- 原审计脚本内置了早期知识库 ID；
- 清理历史知识库后，默认 ID 会失效，导致审计误报；
- 现在如果默认 ID 不可用，脚本会自动从当前知识库列表中选择有文档的知识库；
- 也可以继续通过 `--knowledge-base-id` 显式指定目标知识库。

代码路线：

- `scripts/run_knowledge_base_interview_audit.py`
  - `summarize_coverage()`
  - `summarize_coverage_progress()`
  - `resolve_knowledge_base_id()`
- `tests/unit/test_interview_audit_runner.py`
- `src/agent_mentor/application/profile_service.py`
  - 复用已有 `get_coverage()`，本轮未改核心画像逻辑。

### 10.3 小规模真实验收

验收命令：

```bash
python scripts/run_knowledge_base_interview_audit.py agent \
  --rounds 1 \
  --output docs/evaluations/results/agent-coverage-audit-20260902.json
```

验收结果：

- 默认旧知识库 ID：`46691546-593a-4d21-bcfc-0d16986c20a7`
- 自动解析到当前知识库：`b2d70e40-02d1-4a78-af5a-22df85a82693`
- 完成轮数：1 / 1
- 失败轮数：0
- 题目数：3
- 近似重复题：0
- 运行态版本：`app_version = 0.1.0`
- 运行态启动时间：`2026-09-02T14:07:46.989950+00:00`
- 题目生成模式：`llm = 3`

覆盖变化：

| 指标 | 训练前 | 训练后 | 变化 |
| --- | ---: | ---: | ---: |
| 总知识点 | 150 | 150 | 0 |
| 未覆盖知识点 | 119 | 118 | -1 |
| 已触达但证据不足 | 11 | 12 | +1 |
| 已可信验证 | 20 | 20 | 0 |
| 触达率 | 20.67% | 21.33% | +0.66% |
| 可信覆盖率 | 13.33% | 13.33% | 0 |

解释：

- 本轮训练确实推进了“查漏”，有 1 个知识点从未覆盖变成已触达；
- 可信覆盖率没有变化是合理的，因为这些新触达点还只经历了单轮评分，当前规则仍把它们归为 `insufficient_evidence`；
- 这说明系统区分了“考过一次”和“已经可信掌握”，不会因为一次高分就把画像快速抬高。

### 10.4 本轮暴露的新问题与校正

第一次查看审计 JSON 时，PowerShell 输出中出现了中文乱码，容易误判为 DocumentParser 或数据库入库编码问题。

复核后结论：

- 使用 `PYTHONIOENCODING=utf-8` 重新请求 `/coverage` 后，接口返回中文标题正常；
- 当前知识点目录标题没有发现实际乱码；
- 这不是业务代码问题，而是 Windows PowerShell 子进程输出编码造成的展示假象。

真正暴露的问题是运行态版本滞后：

- 第一次小规模审计时，`/health/runtime` 缺少 `app_version` 和 `started_at`；
- `question_generation_summary` 为空，说明当前 API 容器不是最新业务代码；
- 重建 API 容器后，runtime 元数据和 `generation={'llm': 3}` 均正常。

这说明后续做验收时必须先看运行态快照，确认连接的是最新容器，而不是只看本地源码。

### 10.5 面试表达价值

可以这样讲：

> 我们后续没有只看分数和错题，而是把训练质量拆成补缺和查漏两条线。补缺解决的是“哪里答错了”，查漏解决的是“哪些知识点还没考过”。我复用了画像服务里的 coverage 接口，在审计脚本里记录训练前后覆盖快照，输出触达率、可信覆盖率、新增触达点和剩余未覆盖点。一次小规模真实验收显示，训练后未覆盖点减少，但可信覆盖率没有立刻上升，这符合我们的设计：系统不会因为一次高分就认为用户稳定掌握，而是需要可信评分逐步沉淀。

## 11. 第 6 批训练质量修复：前端运行态证据展示

### 11.1 发现的问题

在覆盖审计中发现，代码已经包含 `app_version`、`started_at`、`generation` 等运行态证据，但如果 Docker 容器没有重建，页面和审计结果可能仍连接到旧运行态。

这个问题对面试演示很敏感：

- 面试官看到页面时，不知道当前到底是本地降级还是 DeepSeek；
- 不知道 embedding 是否已经切到 BGE；
- 不知道 API 容器是否是最新启动版本；
- 需要额外打开命令行解释，演示链路不够自证。

### 11.2 最小改造方案

不改后端接口，只复用已有 `/health/runtime` 返回值，在前端补充展示：

- 侧边栏显示 LLM 状态和 Embedding 模式；
- 总览页指标区展示 API 版本、Embedding、启动时间；
- 系统状态页展示：
  - LLM 状态；
  - Embedding provider / dimension；
  - embedding model；
  - API version；
  - API started_at；
  - 最近 RAG / 最近评分 / 演示就绪度。

代码路线：

- `frontend/src/utils/formatters.js`
  - `runtimeVersionLabel()`
  - `runtimeStartedLabel()`
  - `embeddingLabel()`
- `frontend/src/components/AppLayout.jsx`
- `frontend/src/components/RuntimeInsights.jsx`
- `frontend/src/components/common.jsx`
- `frontend/src/styles.css`

### 11.3 验收结果

本地前端构建：

```bash
npm run build
```

结果：

- Vite build 通过；
- React 页面没有构建错误；
- 运行态字段缺失时会显示“未知”，不会导致页面崩溃。

后端回归：

- `ruff check .`：通过；
- `pyright`：0 errors；
- `pytest`：87 passed，1 skipped。

限制：

- 本轮尝试重建 frontend Docker 容器时，Docker Desktop 引擎不在线，报错为无法连接 `dockerDesktopLinuxEngine`；
- 代码和本地 build 已通过；
- Docker Desktop 恢复后执行 `docker compose up -d --build frontend` 即可让 `http://localhost:3000` 使用新版静态包。

### 11.4 面试表达价值

可以这样讲：

> 我后来发现，仅靠源码和命令行说系统启用了 DeepSeek、BGE 和最新 API，不如让页面自己展示运行态证据。所以我把 `/health/runtime` 的信息接入前端系统状态和总览区，直接展示 LLM 模式、Embedding 模型、向量维度、API 版本和启动时间。这样面试演示时可以现场证明当前跑的不是旧容器，也不是纯本地假数据。

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
- `pytest`：93 passed，1 skipped。

限制：

- 本轮尝试重建 frontend Docker 容器时，Docker Desktop 引擎不在线，报错为无法连接 `dockerDesktopLinuxEngine`；
- 代码和本地 build 已通过；
- Docker Desktop 恢复后执行 `docker compose up -d --build frontend` 即可让 `http://localhost:3000` 使用新版静态包。

### 11.4 面试表达价值

可以这样讲：

> 我后来发现，仅靠源码和命令行说系统启用了 DeepSeek、BGE 和最新 API，不如让页面自己展示运行态证据。所以我把 `/health/runtime` 的信息接入前端系统状态和总览区，直接展示 LLM 模式、Embedding 模型、向量维度、API 版本和启动时间。这样面试演示时可以现场证明当前跑的不是旧容器，也不是纯本地假数据。

## 12. 第 7 批训练质量修复：知识目录噪声清理

### 12.1 发现的问题

覆盖审计已经能告诉我们“哪些知识点没考过”，但进一步查看候选知识点后发现，目录抽取里存在两类噪声：

1. Markdown 代码块里的 `# xxx` 被误识别成标题；
2. 教案类文档中的结构性标题被当成知识点，例如：
   - `一、教案正文`
   - `二、学员疑问与讨论记录`
   - `先说结论`
   - `本课自测`
   - `自测结果`
   - `核心链路图`
   - `最小源码定位表`

这些内容不是知识点，而是文档组织结构。如果进入画像，会带来两个问题：

- 查漏推荐会出现“自测结果”“源码定位表”这类不可训练主题；
- 覆盖率看似完整，但其实混入了非知识节点，降低训练画像可信度。

### 12.2 最小改造方案

本轮仍然不改数据库结构，也不引入 LLM 抽取知识点，只增强确定性规则：

- Markdown parser 识别 fenced code block；
- 代码块里的 `#` 不再当作 Markdown heading；
- catalog title 抽取时先清理编号前缀：
  - `2.1 先说结论` → `先说结论`
  - `一、教案正文` → `教案正文`
  - `第 2 课：知识入库链路` → `知识入库链路`
- 把标题分成两类：
  - 泛标题：可以跳过当前标题，回退父级或正文第一行，例如 `核心知识点`；
  - 非知识标题：直接跳过，不再回退，例如 `自测结果`、`核心链路图`、`源码定位表`。

代码路线：

- `src/agent_mentor/rag/documents.py`
  - `_parse_text()` 增加 fenced code 识别；
  - 解析前去掉 UTF-8 BOM，避免 `#` 标题识别失败。
- `src/agent_mentor/application/coverage_catalog.py`
  - `_clean_catalog_title()`
  - `_is_specific_catalog_title()`
  - `_is_non_knowledge_title()`
  - `_is_non_knowledge_path()`
- `tests/unit/test_documents.py`
- `tests/unit/test_coverage_catalog.py`

### 12.3 离线审计结果

使用 `docs/learning` 下 7 份学习文档做离线扫描，不连接数据库，只验证 parser + chunking + catalog title 抽取效果。

修复后结果：

- 唯一候选知识点：112；
- 关联 chunk：119；
- 跳过非知识结构块：39；
- 顶部候选从“教案正文 / 学员疑问 / 自测结果”变成：
  - `Embedding 阶段：当前的真实实现`
  - `重新索引时为什么尽量保留 Chunk ID`
  - `上传阶段：三个安全措施`
  - `增量知识目录：新文档如何进入查漏体系`
  - `RRF 公式`
  - `引用白名单`
  - `证据门禁`

这说明目录质量明显更接近“可训练知识点”，而不是文档结构标题。

### 12.4 回归结果

- `ruff check .`：通过；
- `pyright`：0 errors；
- `pytest`：93 passed，1 skipped。

跳过项仍是：

- `tests/integration/test_learning_loop.py`
- 原因：未配置独立 PostgreSQL 集成测试库。

### 12.5 生效方式

本次修改会在新文档入库时自动生效。

对于已经入库的旧文档，需要重建 coverage catalog 才会反映到数据库。当前项目在 API 启动时会执行：

```text
main.py
→ knowledge_service.rebuild_coverage_catalogs()
→ sync_document_catalog()
```

因此下一次重建并重启 API 容器后，已有文档的 catalog source 会按新规则刷新。

### 12.6 面试表达价值

可以这样讲：

> 做 coverage 审计后，我发现不是所有 heading 都适合当作知识点。比如教案里的“先说结论”“自测结果”“核心链路图”只是文档结构，如果进入画像，会让查漏推荐失真。我没有直接引入 LLM 抽取，而是先做确定性清洗：Markdown parser 跳过代码块标题，catalog 抽取时清理编号并过滤非知识标题。这样保持实现可控，也让画像中的知识点更接近真实可训练主题。

## 13. 第 8 批训练质量修复：查漏题位优先级排序

### 13.1 发现的问题

项目已经有“固定题位用于覆盖未考知识点”的机制，但进一步审计发现，未覆盖知识点的选择方式是按标题字典序排序。

这会带来一个隐蔽问题：

- 标题排序稳定，但不代表训练优先级合理；
- 可能长期优先考数字或字母更靠前的知识点；
- 新增文档后，重要知识点未必排在前面；
- 查漏机制有了，但“查哪些漏”还不够有依据。

### 13.2 最小改造方案

不改状态机、不改数据库结构，只调整 `_coverage_gap_focus()` 的查询排序：

旧规则：

```text
未覆盖知识点
→ 按 title 升序
→ 取第 1 个
```

新规则：

```text
未覆盖知识点
→ 按关联 chunk 数量倒序
→ 再按 title 升序稳定排序
→ 取第 1 个
```

这样做的含义是：一个知识点如果被多个 chunk 提到，通常说明它在资料里更重要或证据更充分，应该优先进入查漏训练。

代码路线：

- `src/agent_mentor/application/interview_service.py`
  - `_coverage_gap_focus()`
  - `_coverage_gap_focus_statement()`
- `tests/unit/test_interview_service.py`

### 13.3 回归结果

定向测试：

- `tests/unit/test_interview_service.py`：11 passed。

全量测试见本轮最终回归。

### 13.4 面试表达价值

可以这样讲：

> 查漏不是随机从未覆盖点里挑一个，也不是按标题排序。我后来把查漏题位的候选排序改成了“资料来源数优先”：一个知识点关联的 chunk 越多，说明它在当前知识库中越重要或证据越充分，所以优先考。这个改动很小，但让覆盖驱动出题更有解释性。

## 14. 第 9 批训练质量修复：RAG 知识边界与评估口径对齐

### 14.1 发现的问题

在 BGE 运行态下重新执行 `retrieval_v1.jsonl` 检索评估时，最初得到：

```text
negative_rejection_accuracy = 0.0
```

这表示 4 个知识库外问题全部被判为“证据充分”。继续追查后发现问题分成两层：

1. **评估口径落后于生产口径**：`evals/runners/retrieval_runner.py` 只用 top score 判断证据是否足够，而生产 `AnswerService` 还会做 lexical support 检查。
2. **生产边界仍有误放行风险**：如果问题里混入 `RAG`、`Docker` 这类项目泛化词，即使核心限定条件来自知识库外，也可能被误判为有支撑。

典型风险问题：

```text
唐朝开元年间的具体盐税制度如何影响 RAG 系统设计？
Docker Desktop 4.82 的所有发布说明逐条是什么？
```

这类问题不应该只因为包含 `RAG` 或 `Docker` 就被知识库回答。

### 14.2 最小改造方案

本次没有改 RAG 主链路，也没有引入复杂 reranker，只做三点小修：

1. **抽出生产证据门禁方法**
   - 在 `AnswerService` 中新增 `assess_evidence(question, candidates)`；
   - `answer()` 和 retrieval eval 共用同一套证据充分判断。

2. **收紧跨域问题边界**
   - 对 `RAG`、`Docker`、`系统`、`设计` 等泛化词降权；
   - 当问题同时包含英文项目词和大量中文限定实体时，必须有中文关键实体支撑；
   - 避免“项目词命中”掩盖“核心问题知识库外”。

3. **让评估报告暴露失败样本**
   - `retrieval_eval.md` 增加 Evidence Gate Failures；
   - 每个失败样本展示问题、是否可回答、证据充分判断、supported chunk 数、top document 和 top score；
   - 方便后续判断是召回失败、资料缺失，还是边界门禁问题。

代码路线：

- `src/agent_mentor/application/answer_service.py`
  - `assess_evidence()`
  - `_has_lexical_support()`
  - `_requires_specific_chinese_support()`
- `evals/runners/retrieval_runner.py`
  - 使用 `AnswerService.assess_evidence()` 对齐生产口径；
  - 输出失败样本明细。
- `tests/unit/test_retrieval.py`
  - 增加跨域问题拒答测试。

### 14.3 Docker 评估环境补齐

本机直接运行 BGE eval 时，Windows 应用控制策略会拦截 `torch_python.dll`：

```text
WinError 4551 应用程序控制策略已阻止此文件
```

这不是业务代码失败，但会导致本机评估不可用。为保证验收贴近真实运行态，本次把 `evals/` 纳入 api 镜像，使检索评估可以直接在 Docker api 容器里执行。

同时优化 Dockerfile 缓存层：

旧构建方式：

```text
COPY src
pip install .
```

问题是每次源码变动都会重新安装 torch 和 sentence-transformers。

新构建方式：

```text
COPY requirements.txt
pip install torch + requirements
COPY src / migrations / evals
pip install --no-deps .
```

这样依赖层可以命中缓存。实际验证中，后续 api 镜像构建缩短到约 12 秒。

代码路线：

- `Dockerfile`
- `requirements.txt`

### 14.4 验收结果

容器内执行：

```text
python -m evals.run retrieval \
  --knowledge-base-id b2d70e40-02d1-4a78-af5a-22df85a82693 \
  --output-dir evals/reports/retrieval_current
```

修复后结果：

```text
total = 30
Recall@1 = 0.5
Recall@3 = 0.6538
Recall@6 = 0.7308
MRR = 0.5865
evidence_sufficient_accuracy = 0.7667
negative_rejection_accuracy = 1.0
```

结论：

- 知识库外问题已经能稳定拒答；
- 仍有若干可回答问题未命中预期证据，主要表现为召回排序或资料覆盖问题；
- 下一步如果继续优化训练质量，重点应放在“召回质量可解释性”和“评测集与知识库版本绑定”。

### 14.5 面试表达价值

可以这样讲：

> 我做 BGE 后没有只看“流程能跑”，而是补了 retrieval eval。评估时发现一个典型 RAG 边界问题：问题里只要混入 RAG/Docker 这类项目词，系统可能把知识库外问题误判成可回答。我没有简单调高阈值，而是把生产证据门禁抽成 `assess_evidence()`，让 eval 和线上口径一致；再对泛化项目词做边界约束，要求跨域问题必须有具体实体支撑。修复后负例拒答准确率从 0.0 提升到 1.0。这个过程说明我不是只做 demo，而是在用评测发现并收敛 RAG 可信性问题。

## 15. 第 10 批训练质量修复：评分区分度报告可追溯

### 15.1 发现的问题

`evaluation_discrimination_v1.jsonl` 已经能用于验证评分区分度，但评分 eval 报告最初只包含指标，缺少运行态元数据和失败样本摘要。

这会带来两个问题：

- 以后无法确认报告是 deterministic fallback 还是 DeepSeek LLM 跑出来的；
- 如果 MAE 或复核路由不理想，需要重新打开 JSON 才能定位失败样本；
- 面试复盘时很难证明“评分质量是被验证过的”，容易停留在口头描述。

### 15.2 最小改造方案

不改评分逻辑，只增强 eval runner 的报告能力：

1. 在 `ScoringEvalReport` 中补充 metadata：
   - `generated_at`
   - `app_version`
   - `dataset_sha256`
   - `use_llm`
   - `llm_enabled`
   - `llm_model`
2. Markdown 报告增加：
   - 高误差样本：`absolute_error >= 6`
   - 复核路由不一致样本：`expected_review != predicted_review`
3. 保留 baseline 和 LLM 两类评估结果，用于说明：
   - deterministic fallback 是可用降级，不是高质量评分器；
   - DeepSeek LLM 才承担真实评分区分度。

代码路线：

- `evals/runners/scoring_runner.py`
- `evals/reports/discrimination_baseline/scoring_eval.md`
- `evals/reports/discrimination_llm/scoring_eval.md`

### 15.3 验收结果

deterministic baseline：

```text
total = 12
MAE = 7.1667
Pearson correlation = 0.8735
Reviewer routing accuracy = 0.4167
Band order accuracy = 1.0
```

DeepSeek LLM：

```text
total = 12
MAE = 1.6667
Pearson correlation = 0.9802
Reviewer routing accuracy = 1.0
Band order accuracy = 1.0
```

结论：

- LLM 评分对低/中/高质量答案具备明显区分度；
- 复核路由在该评测集上命中预期；
- fallback 适合作为无 Key 环境演示闭环，但不能包装成高质量评分模型。

### 15.4 面试表达价值

可以这样讲：

> 我没有只说“系统能评分”，而是专门做了一个人工答案集，里面同一道能力点准备低分、中分、高分答案，并标注人工期望分。然后用 eval runner 对比模型评分和人工分，输出 MAE、相关系数、档位排序和复核路由准确率。结果显示 DeepSeek 评分 MAE 约 1.67，相关系数 0.98，能稳定区分不同质量答案。同时我也保留 deterministic fallback 的结果，明确它只是无 Key 降级，不把它包装成真实评分能力。

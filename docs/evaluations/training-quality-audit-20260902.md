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

### 2.5 P2：知识点覆盖仍需更长期的查漏机制

表现：

- 当前已有未覆盖知识点优先出题；
- 但新增文档后，知识点目录变大，仍需要观察哪些点长期未覆盖；
- 只看“薄弱项补缺”不够，还要看“未知点查漏”。

建议下一步：

- 审计脚本输出 covered / uncovered / stale 知识点比例；
- 新增文档后自动把新知识点标记为待覆盖；
- 面试计划中保留固定题位用于查漏。

状态：部分已做，仍可增强。

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

### 8.6 面试表达价值

可以这样讲：

> 我没有只用参考答案跑通流程，因为那会让评分结果天然偏高。为了验证评分器是否真的有区分度，我构造了同题低、中、高三档人工答案集，并扩展 Eval Runner 统计 MAE、相关性、复核命中率和分档排序。第一版 baseline 暴露出本地 fallback 评分偏保守的问题，这也证明这个评估不是摆设，而是能发现系统缺陷。后续使用真实 LLM 评分时，就可以对比 fallback 和 LLM 的区分度差异。

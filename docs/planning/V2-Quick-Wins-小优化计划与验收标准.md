# AgentMentor V2 Quick Wins 小优化计划与验收标准

> 日期：2026-08-08
> 定位：面试前小质量增强，不替代 V1/V2 主路线。
> 目标：用低风险改动提升“画像闭环真实性、RAG 可量化评估、幂等可靠性、Embedding 演进可讲性”。

---

## 一、改造原则

1. 不做大规模架构重构。
2. 不破坏当前 Docker Compose 本地运行链路。
3. 不默认引入重依赖导致 16GB 开发机演示不稳定。
4. 优先增强能被面试官追问、能被测试证明的能力。
5. 每完成一项都必须跑对应测试，再决定是否进入下一项。

---

## 二、阶段拆分

### Quick Win 1：覆盖保底出题策略

#### 背景

当前 `ProfileService.recommend_interview_plan()` 会推荐 `uncovered`、`attempted`、`insufficient_evidence` 知识点，但用户如果一直选择熟悉主题，部分知识点可能长期不被考到。这样画像虽然能补缺，但查漏能力还不够硬。

#### 目标

在不改变用户选择主题的前提下，为每轮面试保留一个“覆盖盲区题位”。当知识库中存在未覆盖知识点时，系统优先让某一题围绕未覆盖点出题。

#### 实现范围

- `src/agent_mentor/application/interview_service.py`
- `src/agent_mentor/application/profile_service.py`
- `tests/unit/` 或 `tests/integration/`

#### 设计约束

- 不叫“强制出题”，对外表述为“覆盖保底出题策略”。
- 默认三题面试中第 2 题优先覆盖 `uncovered` 知识点。
- 第一版只处理 `uncovered` 覆盖盲区；`attempted` / `insufficient_evidence` 作为后续增强，不在本轮小优化里扩大策略复杂度。
- 若没有覆盖缺口，继续走原有出题逻辑。
- 题目必须仍然基于检索片段生成，不能只拿知识点标题硬编题。
- 出题后必须写入 `QuestionCoveragePoint`，让覆盖状态能被后续统计消费。

#### 验收标准

- [x] 当知识库存在 `uncovered` 知识点时，第 2 题查询文本会优先包含该知识点。
- [x] 当不存在覆盖缺口时，原有出题逻辑不受影响。
- [ ] 生成题目仍然包含引用 chunk。
- [ ] `ProfileService.get_coverage()` 能在题目生成后看到对应知识点从 `uncovered` 进入已尝试链路。
- [x] 新增测试覆盖“存在 uncovered 时优先考查”和“无 uncovered 时回退原逻辑”。
- [x] `ruff check src/agent_mentor/application/interview_service.py tests/unit/test_interview_service.py` 通过。
- [x] `pyright src/agent_mentor/application/interview_service.py tests/unit/test_interview_service.py` 通过。
- [x] `pytest tests/unit/test_interview_service.py tests/unit/test_retrieval.py tests/unit/test_profile.py` 通过。

---

### Quick Win 2：Retrieval Eval Runner 第一版

#### 背景

`evals/datasets/retrieval_v1.jsonl` 已经存在，但当前缺少自动 runner。没有指标，就无法证明检索改造是否真的变好。

#### 目标

先实现检索评估，不做评分评估。用固定数据集输出可复现指标，为后续 BGE 切换和分块优化提供基线。

#### 实现范围

- `evals/run.py`
- `evals/metrics.py`
- `evals/runners/retrieval_runner.py`
- 如有必要，补充 `evals/README.md`

#### 第一版指标

- `Recall@1`
- `Recall@3`
- `Recall@6`
- `MRR`
- negative query 拒答准确率
- evidence sufficient 判断准确率

#### 设计约束

- 第一版只读取 `retrieval_v1.jsonl`。
- 优先支持离线/本地运行。
- 不改 `EvaluationService`。
- 不引入 BGE 依赖。
- 输出 JSON 和 Markdown 两种报告，便于面试展示。

#### 验收标准

- [x] 可以通过命令运行检索评估。
- [x] 可以读取 `evals/datasets/retrieval_v1.jsonl`。
- [x] 输出包含 Recall@1/3/6、MRR、拒答准确率、证据充分率。
- [x] 评估结果写入 `evals/reports/`。
- [x] 数据集为空或格式错误时有清晰错误提示。
- [x] 新增 metrics 单元测试。
- [x] `ruff check evals tests/unit/test_eval_metrics.py ...` 通过。
- [x] `pyright evals tests/unit/test_eval_metrics.py ...` 通过。
- [x] `pytest tests/unit/test_eval_metrics.py ...` 通过。

---

### Quick Win 3：答题幂等补强检查

#### 背景

当前数据库模型已经存在唯一约束：

```python
UniqueConstraint("question_id", "idempotency_key", name="uq_answer_idempotency")
```

因此不需要重复做“加唯一约束 + 迁移”。真正需要确认的是并发冲突下是否能优雅返回已有 snapshot。

#### 目标

保留“应用层先查 + 数据库唯一约束兜底”的三层设计，补充 `IntegrityError` 处理和测试，确保并发重复提交不会破坏面试状态。

#### 实现范围

- `src/agent_mentor/application/interview_service.py`
- `tests/unit/` 或 `tests/integration/`

#### 设计约束

- 不移除应用层先查逻辑。
- 捕获唯一约束冲突后必须 rollback，再重新读取面试 snapshot。
- 不新增 Alembic 迁移，除非发现数据库迁移文件缺失该约束。

#### 验收标准

- [x] 确认 model 和 migration 均包含 `uq_answer_idempotency`。
- [x] `submit_answer` 在唯一约束冲突时能 rollback 并返回已有 snapshot。
- [x] 重复提交同一 `Idempotency-Key` 不会新增答案。
- [x] 重复提交不会重复推进题目。
- [ ] 新增测试覆盖唯一约束冲突路径。
- [x] `ruff check ... interview_service.py` 通过。
- [x] `pyright ... interview_service.py` 通过。
- [x] `pytest tests/unit/test_interview_service.py ...` 通过。

---

### Quick Win 4：BGE Embedding 前置准备

> 现状更新：本节记录的是当时的低风险 Quick Win 计划。后续已按“重建式切换”完成 BGE 落地：默认 `embedding_provider=bge` 时使用 `BAAI/bge-small-zh-v1.5`，pgvector 维度调整为 512，历史向量不做在线迁移，重新导入资料生成新向量；同时保留 `DevelopmentEmbeddingGateway` 作为测试和无模型环境 fallback。

#### 背景

当前 `DevelopmentEmbeddingGateway` 是特征哈希开发基线，优势是确定、轻量、离线可运行；短板是语义召回上限较低。直接默认切换 BGE 会引入依赖、模型下载、向量维度迁移和重索引风险，不适合作为面试前低风险改造。

#### 目标

本轮只做 BGE 切换的前置准备：把演进路径讲清楚，并增加必要的配置/维度保护。不默认启用 BGE，不引入重依赖，不改现有向量维度。

#### 实现范围

- `src/agent_mentor/config.py`
- `src/agent_mentor/main.py`
- `src/agent_mentor/infrastructure/embedding.py`
- 文档或注释说明

#### 设计约束

- 默认仍使用 `DevelopmentEmbeddingGateway`。
- 不把 pgvector 维度从 1536 改为 512。
- 不新增 `sentence-transformers` 依赖。
- 增加启动期维度一致性校验或显式说明。
- BGE 作为后续可选 Provider，不影响当前 Docker 演示。

#### 验收标准

- [x] 当前默认 Embedding 行为不变。
- [x] 若配置维度与数据库向量维度不一致，系统能给出清晰错误或健康检查提示。
- [x] 文档明确说明：当时 BGE 是后续增强项，切换前应先跑 Retrieval Eval Runner 建立基线；后续版本已完成 BGE 重建式切换。
- [x] 不引入重依赖，不触发模型下载。
- [x] `ruff check ... config.py main.py health.py ...` 通过。
- [x] `pyright ... config.py main.py health.py ...` 通过。
- [x] `pytest tests/unit/test_config.py tests/unit/test_health.py ...` 通过。

---

## 三、推荐执行顺序

1. Quick Win 1：覆盖保底出题策略
2. Quick Win 2：Retrieval Eval Runner 第一版
3. Quick Win 3：答题幂等补强检查
4. Quick Win 4：BGE Embedding 前置准备

理由：

- 覆盖保底出题直接增强核心卖点“画像驱动长期训练闭环”。
- Eval Runner 给后续 RAG 优化提供量化证据。
- 幂等补强风险低，但当前唯一约束已存在，所以排在检查补强位。
- BGE 切换收益大，但依赖和迁移风险也大，本轮只做前置准备。

---

## 四、整体验收清单

### 功能验收

- [ ] 可以完成一轮三题模拟面试。
- [ ] 存在未覆盖知识点时，面试中至少一题优先考查覆盖缺口。
- [ ] 面试完成后可以生成评分报告。
- [ ] 画像和覆盖度可以根据新一轮结果更新。
- [ ] 重复提交答案不会重复写入或重复推进。
- [ ] 可以运行 Retrieval Eval Runner 并生成报告。

### 工程验收

- [ ] `ruff check .` 通过。
- [ ] `pyright` 通过。
- [ ] `pytest` 通过。
- [ ] Docker Compose 可启动。
- [ ] `/health/ready` 正常。
- [ ] 前端页面可打开。

### 面试表达验收

- [ ] 能解释“补缺”和“查漏”的区别。
- [ ] 能解释为什么覆盖保底出题比纯推荐更能证明闭环真实。
- [ ] 能用指标解释 RAG 改造，而不是凭感觉说效果变好。
- [ ] 能说明幂等的三层防线：前端防抖、应用层先查、数据库唯一约束。
- [ ] 能诚实说明：当前默认 BGE-small-zh 已落地，但它不是企业级向量服务；development 特征哈希只是测试/无模型环境 fallback。

---

## 五、本轮不做的事项

- 不做 Repository Port 大重构。
- 不迁移到 LangGraph Runtime。
- 当时本轮不默认切换 BGE；后续版本已采用重建式方案完成默认 BGE 落地。
- 不修改 pgvector 维度。
- 不引入多租户、认证、权限、队列等企业级能力。
- 不重写前端整体布局。

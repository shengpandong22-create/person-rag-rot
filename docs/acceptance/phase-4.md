# Phase 4 验收报告：可信评分、复核与面试报告

## 完成范围

Phase 4 已在 Phase 3 面试主流程之上补齐正式 Evaluation 链路：

- 四维评分契约：Correctness、Completeness、Reasoning、Communication，单维 0-5。
- Rubric 权重校验：权重总和必须为 100，否则拒绝评分。
- 应用层总分计算：模型/评分器输出不得覆盖最终 total。
- 评分引用校验：Evaluation 只能引用当前题目允许的 `question_references.chunk_id`。
- 低置信与争议复核路由：支持 `final`、`review_pending`、`disputed` 状态。
- Reviewer 不可用时保留 `review_pending`，不伪造复核完成。
- 面试报告：汇总总分、维度分布、知识点摘要、低置信/争议项和下一步建议。
- 初始人工评分样本集：20 条 JSONL 样本，作为 Phase 4 baseline。

本阶段仍然遵守 16GB 普通开发机、Docker Compose、本地 pgvector、默认 Fake/确定性实现的工程约束。

## 主要变更文件

- `src/agent_mentor/domain/evaluation.py`
- `src/agent_mentor/application/evaluation_service.py`
- `src/agent_mentor/api/evaluations.py`
- `src/agent_mentor/main.py`
- `src/agent_mentor/infrastructure/database/models.py`
- `migrations/versions/20260719_0005_evaluation_report.py`
- `src/agent_mentor/prompts/evaluation_v1.md`
- `src/agent_mentor/prompts/review_v1.md`
- `evals/datasets/evaluation_v1.jsonl`
- `tests/unit/test_evaluation.py`

## 数据库变更

新增表：

- `evaluations`
- `evaluation_references`
- `interview_reports`

当前容器内 Alembic 版本：

```text
20260719_0005 (head)
```

## 自动化验收

已执行：

```powershell
docker run --rm -v "D:\AgentStudy\personal-rag-bot:/work" -w /work personal-rag-bot-api sh -c "python -m pip install 'ruff>=0.8,<1.0' >/tmp/ruff-install.log && python -m ruff check --fix src tests migrations && python -m ruff format src tests migrations && python -m ruff check src tests migrations"
python -m uv run pyright
python -m uv run pytest
```

结果：

- Ruff：All checks passed
- Pyright：0 errors, 0 warnings
- Pytest：23 passed

覆盖的关键验收点：

- Rubric 权重不为 100 时拒绝。
- 四维分数越界时由 Pydantic 拒绝。
- 总分由应用层 `total_score()` 计算。
- 低置信结果进入 review route。
- Reviewer 不可用时路由到 `review_pending`。
- 非法 chunk 引用抛出 `EVALUATION_CITATION_INVALID`。
- 固定输入下评分结果和引用范围确定。

## 容器与功能验收

已执行：

```powershell
docker compose up -d --build
docker compose exec api alembic current
```

结果：

- `api` 正常启动。
- `db` healthy。
- Alembic 当前版本为 `20260719_0005 (head)`。

使用既有三题完成态面试会话：

```text
interview_id = 133a2bad-8234-4839-a7e5-54f0e0b8a2b9
```

执行：

```http
POST /api/v1/interviews/{interview_id}/evaluations
POST /api/v1/interviews/{interview_id}/report
GET  /api/v1/interviews/{interview_id}/report
```

结果摘要：

```json
{
  "evaluation_count": 3,
  "report_total": 34,
  "report_max": 60,
  "low_confidence_count": 0,
  "disputed_count": 0,
  "first_status": "final",
  "first_references": 2
}
```

报告读取复查：

```json
{
  "total": 34,
  "max": 60,
  "evaluations": 3,
  "next_steps": 2
}
```

## 资源快照

```text
personal-rag-bot-api-1   74.23MiB / 2GiB
personal-rag-bot-db-1    40.04MiB / 2GiB
```

该结果满足“可在 16GB 普通开发机上通过 Docker Compose 部署”的约束。

## 已知限制

- 当前 Evaluator/Reviewer 是确定性基线实现，不调用真实 LLM；这是为了先锁定评分契约、路由和可追溯数据结构。
- Follow-up 当前只产出 `follow_up_recommended`，尚未扩展为独立追问会话节点；V1 后续可在保持“一题最多一次追问”的约束下继续细化。
- 评分样本集已有 20 条，但尚未实现离线评分指标脚本；完整评测统计留到 Phase 6 汇总。

## 退出条件

Phase 4 退出条件已满足：

- 正式 Evaluation 已替代 Phase 3 占位反馈。
- 低置信、复核中和争议结果具备明确状态。
- 报告可追溯到题目、答案、Rubric、评分和引用。
- Phase 5 已解锁。

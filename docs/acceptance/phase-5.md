# Phase 5 验收报告：能力画像、错题与复习闭环

## 完成范围

Phase 5 已在 Phase 4 Evaluation 结果之上补齐学习闭环：

- 能力画像：按用户与知识点维护 `mastery_score`、置信加权次数、版本号和最后来源 Evaluation。
- 错误模式：按知识点聚合固定错误类型，包括概念混淆、细节缺失、推理错误、表达不清等。
- 复习任务：根据错误重复次数和掌握度生成复习任务，支持到期时间、优先级和完成状态。
- 幂等处理：每个 Evaluation 只允许生成一条 `profile_update_events`，重复调用不会重复更新画像。
- 可信边界：`disputed` 与 `review_pending` Evaluation 不更新能力画像，只记录跳过事件。
- 个性化面试计划：新增推荐接口，根据 open 复习任务和低掌握度知识点建议下一轮训练方向；用户显式指定 topic 仍优先于系统推荐。

本阶段继续遵守 16GB 普通开发机、Docker Compose、本地 PostgreSQL/pgvector、确定性业务规则的工程约束。

## 主要变更文件

- `src/agent_mentor/domain/profile.py`
- `src/agent_mentor/application/profile_service.py`
- `src/agent_mentor/api/profiles.py`
- `src/agent_mentor/main.py`
- `src/agent_mentor/infrastructure/database/models.py`
- `migrations/versions/20260719_0006_profile_review_loop.py`
- `tests/unit/test_profile.py`

## 数据库变更

新增表：

- `ability_profiles`
- `error_patterns`
- `review_tasks`
- `profile_update_events`

当前容器内 Alembic 版本：

```text
20260719_0006 (head)
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
- Pytest：29 passed

覆盖的关键验收点：

- `disputed` 和 `review_pending` 不更新画像。
- 低置信但 final 的 Evaluation 使用降权更新。
- 掌握度更新受分数、置信度和难度影响，并保持边界。
- 错误类型由最低维度确定。
- 复习间隔按第 1/2/3 次错误推进为 1/3/7 天。
- 复习任务优先级结合重复次数与掌握度。

## 容器与功能验收

已执行：

```powershell
docker compose up -d --build
docker compose exec api alembic current
```

结果：

- `api` 正常启动。
- `db` healthy。
- Alembic 当前版本为 `20260719_0006 (head)`。

使用既有三题完成态面试会话：

```text
interview_id = 133a2bad-8234-4839-a7e5-54f0e0b8a2b9
```

执行：

```http
POST /api/v1/interviews/{interview_id}/profile-updates
GET  /api/v1/profiles/me/abilities
GET  /api/v1/profiles/me/error-patterns
GET  /api/v1/review-tasks
POST /api/v1/review-tasks/{task_id}/complete
GET  /api/v1/profiles/me/interview-plan
```

画像更新结果摘要：

```json
{
  "snapshot_abilities": 1,
  "abilities": 1,
  "errors": 1,
  "review_tasks": 1,
  "first_mastery": 0.5341,
  "first_task_status": "open"
}
```

幂等复跑结果：

```json
{
  "before_mastery": 0.5341,
  "after_mastery": 0.5341,
  "before_version": 3,
  "after_version": 3
}
```

复习任务完成结果：

```json
{
  "status": "completed",
  "completed_at_present": true
}
```

下一轮面试计划推荐：

```json
{
  "recommendations": 1,
  "first_point": "RAG",
  "first_reason": "low_mastery"
}
```

## 资源快照

```text
personal-rag-bot-api-1   75.09MiB / 2GiB
personal-rag-bot-db-1    39.56MiB / 2GiB
```

该结果满足“可在 16GB 普通开发机上通过 Docker Compose 部署”的约束。

## 已知限制

- 当前能力画像是确定性规则更新，不引入黑盒模型直接覆盖掌握度。
- 复习任务已支持创建与完成，但尚未生成相似题；相似题展示可在 Phase 6 演示层串联已有面试题生成能力。
- 当前推荐接口返回训练知识点建议，不自动替用户创建下一场面试；用户显式选择仍优先。

## 退出条件

Phase 5 退出条件已满足：

- 画像数据能消费可信 Evaluation，并影响下一轮训练建议。
- 所有画像变化都可追溯到 Evaluation 与 `profile_update_events`。
- 错误模式与复习任务形成可通过 API 演示的闭环。
- `disputed` 与 `review_pending` 不会强行更新画像。
- Phase 6 已解锁。

# Shadow Agent 画像零污染审计协议

## 目的

验证开启 Shadow Agent 后，不会修改学习业务状态。审计只允许新增一条 `shadow_agent_runs` 轨迹记录。

## 受保护表

- `ability_profiles`；
- `error_patterns`；
- `review_tasks`；
- `profile_update_events`；
- `evaluations`；
- `knowledge_catalog_points`。

## 执行方式

1. 对指定用户和知识库读取每张受保护表的有序 JSONB SHA-256 指纹；
2. 以 `llm=None` 运行一次 Shadow Agent fallback；
3. 再次计算相同指纹；
4. 断言六张表的指纹逐张完全一致；
5. 断言 `business_writes=0`；
6. 断言 `shadow_agent_runs` 行数恰好增加 1。

使用 fallback 的原因是：本审计验证的是读取工具、Agent service 和 SQLAlchemy trace repository 的数据库副作用边界，而不是模型质量。真实模型质量已由独立语义 Development 协议衡量。

## 通过条件

所有受保护表指纹一致，`business_writes=0`，审计表增量恰为 1。任一失败都禁止开启 feature flag 或接入前端。

## 固定命令

```powershell
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\python.exe -m evals.shadow_agent_zero_write_audit `
  --knowledge-base-id <existing-id> `
  --output evals\reports\shadow_agent_zero_write_audit.json
```


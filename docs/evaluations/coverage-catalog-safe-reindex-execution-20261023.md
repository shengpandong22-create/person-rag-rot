# BGE 知识库目录安全重索引执行记录（2026-10-23）

## 授权与范围

用户已明确授权按 `docs/design/coverage-catalog-safe-reindex-plan-20261022.md` 执行。目标知识库为 `b2d70e40-02d1-4a78-af5a-22df85a82693`，处理 7 份活动 Markdown 文档。

本次只调用逐文档 `POST /api/v1/documents/{id}/reindex`。不删除文档、chunk、历史题目、评分、画像、复习任务或历史 coverage mapping；也没有执行批量删除 catalog points。

## 保护措施

- 操作前保存只读健康审计与逐文档目录 diff 到本地 `backups/catalog-reindex-20261023/`（该目录被 gitignore，避免提交真实数据库内容）。
- 保存相关表逻辑备份 `catalog-tables-before.sql`，SHA-256 为 `d54aa5da483fa6c6b3822aef6458fd2d3896c69e5dd2cbead0bbc7118eb1ebf9`。
- 每份文档单独提交重索引请求，等待 document status 回到 `ready` 后才处理下一份。
- 第 7 份文档的首次执行日志 ID 与审计 UUID 不一致，因此不采信该日志；已用审计确认的 `f99f3cf3-a34f-4b24-a46e-52f90e3f3623` 单独重跑并确认 `ready`。

## 结果

| 指标 | 重索引前 | 重索引后 | 结论 |
|---|---:|---:|---|
| 可信目录点 | 99 | 99 | 未下降 |
| qualified uncovered | 65 | 65 | 未下降 |
| 可信 source-provenance coverage mappings | 267 | 267 | 未下降 |
| provenance mismatch mappings | 16 | 16 | 未扩大 |
| provenance missing-reference mappings | 220 | 220 | 未扩大 |
| 当前规则会新增标题 | 0 | 0 | 无规则漂移 |
| 当前规则会解除标题 | 0 | 0 | 无规则漂移 |

最终机器证据：

- `docs/evaluations/coverage-health-audit-20261023-reindex-after.json`
- `docs/evaluations/catalog-reindex-audit-20261023-after.json`

## 重要边界

审计中发现的 96 个 orphan catalog point 仍然存在，这是预期结果：安全重索引只重建 source links，不会破坏性删除历史点。当前 coverage 读取已经只信任 source-backed 点，所以这些 orphan 不会被当成可信训练目标。

若未来需要物理清理 orphan 点，应另行设计“可恢复删除 + 历史映射保留/迁移”方案；不能把这次安全 reindex 表述为已经完成了 orphan 清理。

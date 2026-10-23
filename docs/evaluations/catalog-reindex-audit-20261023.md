# 现有 BGE 知识库目录重索引只读审计（2026-10-23）

## 范围与安全性

审计对象为 BGE 知识库 `b2d70e40-02d1-4a78-af5a-22df85a82693` 的 7 份活动文档。使用 `scripts/audit_catalog_reindex_plan.py` 仅读取文档、活动 chunks、现有目录点与 source links；没有执行重建、删除、归档或更新。

机器可读明细：`docs/evaluations/catalog-reindex-audit-20261023.json`。

## 发现

| 项目 | 结果 |
|---|---:|
| 活动文档 | 7 |
| 根据当前规则会新增的标题 | 0 |
| 根据当前规则会解除的标题 | 0 |
| 无 source link 的历史目录点 | 96 |

逐文档的当前 source links 与当前分类规则得到的候选标题集一致，说明**现有 source-backed 目录没有出现本轮规则漂移**。每个文档仍检出了结构/自测/演示型 heading，并被 `rejected_non_knowledge_leaf` 或 `rejected_container_heading` 拒绝，不再计作覆盖债务。

96 个 orphan 点是事实异常：这些历史点目前没有 `knowledge_catalog_sources` 关联，因此不能作为可证据支撑的覆盖目标。审计不能从现有数据安全地推断它们何时或为何失联，也没有擅自删除它们。

## 决策

1. 当前生产读取路径已经只将有 source link 的目录点计入 coverage；因此不需要为了这次审计强制写库修复。
2. 若要清理 96 个 orphan 点，必须先按 `docs/design/coverage-catalog-safe-reindex-plan-20261022.md` 导出逐文档 diff、由人工确认，再在备份与可回退窗口中执行。
3. 这份报告不能称为“已完成重索引”；它是执行前的证据与风险边界。

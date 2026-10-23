# 既有知识库目录安全重索引方案

## 原则

既有知识库的文档、chunk、问答、画像、评分和历史引用均不删除、不重置。目录质量改造与向量
重索引无关，不得覆盖用户数据。

## 先审计，后批准

1. 对指定知识库运行只读命令：

   ```powershell
   .\.venv\Scripts\python.exe scripts\audit_coverage_health.py <knowledge-base-id> --output <report.json>
   ```

2. 人工查看 `review_required_catalog_points`，确认被排除的是示例、图、复盘标题等，且没有误伤
   真实训练点。
3. 由用户明确批准后，逐文档调用已有的 `POST /api/v1/documents/{id}/reindex`；每次只处理一个
   文档，等待它回到 `ready`，并重新运行审计。
4. 比对重索引前后的目录数量、标题差异、source link 数、覆盖统计。若出现意外下降，停止后续
   文档，不做批量重置。

## 不做的操作

- 不批量删除 `knowledge_catalog_points`；
- 不删除历史 `question_coverage_points`；
- 不修改用户画像、复习任务或评分；
- 不在没有人工审计和用户确认时对 BGE 验收知识库执行重索引。

旧映射即使保留，也会在新统计规则下因缺失 source-provenance 自动失效，不需要破坏性迁移。

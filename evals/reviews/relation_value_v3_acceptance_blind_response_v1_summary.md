# Relation-Value V3 独立盲审复核摘要

## 复核边界

- 复核人未查看作者标签、候选输出、既有 review/audit/report、V3 实现或 acceptance dataset。
- 未运行 V3、检索或模型。
- 判断仅依据盲审 worksheet、acceptance dataset design 和 worksheet 所引课程原始证据。

## 方法

逐条先确定问题实际请求的 subject/predicate 与关系角色，再独立判断数值语义、单位、模态和证据结构边界；最后填写 accepted value sets 与 provenance。负例不沿用证据中的诱导数字，而是明确记录关系角色、指标语义、主谓绑定、单位、来源结构或缺失值错误前提中的具体不匹配。

## 完成情况与总体结论

- 共完成 36/36 条 reviewer annotation，无遗漏。
- 24 条判为 `answerability=full`，均有至少一个正向 demand；其中多值与多 demand 条目按问题顺序记录。
- 12 条判为 `answerability=none`，均将 `accepted_value_sets` 与 `evidence_ids` 留空。
- 负例分类为：`relation_role` 2 条、`value_semantic` 2 条、`subject_predicate` 2 条、`unit_binding` 2 条、`provenance_structure` 2 条、`missing_value_false_premise` 2 条。
- 未发现无法确定或必须移除的条目。个别数值可有等价字符串表示时，仅在语义和单位不变的前提下记录等价集合（如 `1.0`/`1`、`v3`/`3`）。

## 逐条状态

| ID | 结论 | 复核要点 |
| --- | --- | --- |
| rva3-001 | full | 本地内存约束 16GB |
| rva3-002 | full | 旧块索引 3 到 4 |
| rva3-003 | full | 应用层总分 13；LLM 错写 15 |
| rva3-004 | full | FINAL 条件分差 `<5` |
| rva3-005 | full | 复核触发下界 4 |
| rva3-006 | full | 掌握度 0.40 到 0.47 |
| rva3-007 | full | completeness 范围 0 到 5 |
| rva3-008 | full | reasoning 范围 0 到 5 |
| rva3-009 | full | communication 范围 0 到 5 |
| rva3-010 | full | disputed/review_pending 权重 0 |
| rva3-011 | full | 高置信 FINAL 权重 1.0 |
| rva3-012 | full | A 的向量/全文排名 1、3 |
| rva3-013 | full | 首题 sequence 1 |
| rva3-014 | full | 保留 4 位小数 |
| rva3-015 | full | FastAPI Router 7 个路由 |
| rva3-016 | full | rank 从 1 开始 |
| rva3-017 | full | 最多前三个候选 |
| rva3-018 | full | 历史 v3；新内容 v4 |
| rva3-019 | full | D 的 RRF 结果 0.0320 |
| rva3-020 | full | C 的 RRF 结果 0.0164 |
| rva3-021 | full | B 的 RRF 结果 0.0161 |
| rva3-022 | full | easy/medium/hard 为 0.85/1.0/1.15 |
| rva3-023 | full | streak 封顶 2 |
| rva3-024 | full | 英文词至少 2 字符 |
| rva3-025 | none | 阈值不构成绝对正确保证 |
| rva3-026 | none | 封顶/完成条件不构成排他写入保证 |
| rva3-027 | none | 内存容量不是并发用户数 |
| rva3-028 | none | 总分不是 P95 延迟 |
| rva3-029 | none | completeness 行不证明 correctness |
| rva3-030 | none | 权重 0 属于 disputed/review_pending |
| rva3-031 | none | 评分范围不是天数 |
| rva3-032 | none | GB 不能绑定为毫秒 |
| rva3-033 | none | 首题值不能外推恢复后第二题 |
| rva3-034 | none | 当前 chunk 版本不能外推另一文档 |
| rva3-035 | none | 未给出线上 P95 |
| rva3-036 | none | 未给出生产 QPS |

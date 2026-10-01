# Low-overlap Semantic Candidate Recall Diagnostics

## 范围

仅分析冻结 trigger-development fixture 中 4 条 `low_overlap_semantic_positive`。
配置保持 `vector-only + heading-shadow + consumption=none`，未修改检索算法或阈值。

## 损失漏斗

| 样本 | vector raw rank | post-filter rank | 主 Top-6 | heading supplemental rank | 归因 |
| --- | ---: | ---: | ---: | ---: | --- |
| `trg-lp-001` | 无 | 无 | 未命中 | 无 | vector candidate miss |
| `trg-lp-002` | 7 | 7 | 未命中 | 无 | ranking cutoff |
| `trg-lp-003` | 10 | 9 | 未命中 | 18 | ranking cutoff |
| `trg-lp-004` | 无 | 无 | 未命中 | 无 | vector candidate miss |

汇总：

- vector candidate Recall@20：`0.50`
- 主 Recall@6：`0.00`
- heading supplemental Recall@20：`0.25`
- candidate 缺失：2/4
- Top-6 排序截断：2/4
- diversity filter 不是这四条的主要损失来源

## 结论

问题不是一个统一的“Top-6 太小”：

1. `trg-lp-002`、`trg-lp-003` 已进入 vector candidate pool，适合研究不改变已有
   Top-6 的二阶段语义判别或安全补充；
2. `trg-lp-001`、`trg-lp-004` 在 candidate@20 中不存在，任何后排序、配额、去重或
   Gate 调整都无法救回；
3. heading lexical 对语义改写覆盖不足，不能承担通用 candidate recall 扩展职责。

## 下一实验边界

已完成 eval-only `candidate_k=50` 诊断：

| 样本 | candidate_k=20 raw rank | candidate_k=50 raw rank |
| --- | ---: | ---: |
| `trg-lp-001` | 无 | 无 |
| `trg-lp-002` | 7 | 7 |
| `trg-lp-003` | 10 | 10 |
| `trg-lp-004` | 无 | 无 |

两条 candidate miss 扩到 Top-50 后仍然缺失，证明它们不是候选深度不足，而是当前
embedding 查询视图没有建立所需语义对应。另两条的排序位置也完全不变。提高生产
candidate_k 不具备候选资格。

下一步应比较预先固定的语义查询改写或独立语义召回路，并保持原 vector Top-6
单调安全。每种语义视图必须单独消融，不能与过滤、Gate 或 RRF 权重同时变化。

不调整 RRF 权重，不把 Gate 失败归入检索算法，也不运行 validation/holdout。

机器可读结果：

- `trigger_development_baseline/split_diagnostics.json`
- `trigger_development_candidate_depth_50/retrieval_eval.json`

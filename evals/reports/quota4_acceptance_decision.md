# Quota-4 独立检索验收结论

## 结论

**候选不通过，生产默认保持 `max_chunks_per_document=3`。**

本次是冻结验收集上的唯一一次运行。结果不得用于修改该验收集、调整门槛后重跑，或针对逐题失败继续优化 quota-4 候选。通过验收原本只代表具备生产切换评审资格；本次未达到该资格。

## 冻结事实

- 验收集：`evals/datasets/retrieval_quota4_acceptance_v1.jsonl`
- 数据集 SHA-256：`da6f8a563a8fa6b1b66ecc6868e0626797885892282885b7daa883cd8f9d6f1b`
- 冻结清单 SHA-256：`fad8dbc00a69c1c6beb7536884e275497f5d6472c10f06bca1c0c76dd1d86615`
- 冻结提交：`b61ea5a823a7c244a189c46709f87065801145fe`
- 候选实现：`b791ef6bb39f162529ccd475455d30b9ade78e41`
- 配置：`vector-only / top_k=6 / candidate_k=20 / quota=4`
- 数据规模：18 条（12 full、2 partial、4 none）
- ground truth：14 条 resolved、4 条 absent、0 条 unresolved
- 知识库：7 个 active/ready 文档、195 chunks
- Embedding：`BAAI/bge-small-zh-v1.5`，512 维
- 运行时间：2026-09-29T12:11:51.553869+00:00
- 总检索耗时：32678.8894 ms

## 预注册门槛对照

| 指标 | 门槛 | 实测 | 判定 |
| --- | ---: | ---: | --- |
| source label unresolved | 0 | 0 | 通过 |
| Recall@6 | ≥ 0.75 | 0.5000 | **失败** |
| MRR | ≥ 0.45 | 0.3988 | **失败** |
| full answerability accuracy | ≥ 0.75 | 0.9167 | 通过 |
| partial answerability accuracy | ≥ 0.50 | 0.5000 | 通过 |
| negative rejection accuracy | 1.00 | 0.2500 | **失败** |

补充指标：Recall@1=0.3571、Recall@3=0.4286、candidate Recall@20=0.7857、pre-filter Recall@6=0.6429、P50=45.4311 ms、P95=31951.0801 ms、平均返回候选数=6.0。

## 失败归因

### 正样本检索与排序

| 样本 | 类别 | 关键信号 |
| --- | --- | --- |
| q4a-pos-004 | adjacent_filter_miss | 相关证据 raw rank=3，被相邻块过滤 |
| q4a-pos-006 | per_document_filter_miss | 相关证据 raw rank=18，被每文档限额过滤 |
| q4a-pos-007 | adjacent_filter_miss | 相关证据 raw rank=3，被相邻块过滤 |
| q4a-pos-009 | candidate_recall_miss | candidate@20 内无相关证据 |
| q4a-pos-010 | ranking_cutoff_miss | raw rank=14、post-filter rank=13，未进入 top 6 |
| q4a-pos-011 | candidate_recall_miss | candidate@20 内无相关证据 |
| q4a-pt-001 | candidate_recall_miss | candidate@20 内无相关证据 |
| q4a-pt-002 | evidence_gate_rejection | 相关证据 rank=1，但 Gate 拒绝 |

召回损失并非单一 quota 参数可以解释：3 条 candidate recall miss、2 条 adjacent filter miss、1 条 per-document filter miss、1 条 cutoff miss。quota=4 只放宽每文档数量，无法覆盖其余主要损失来源。

### 负样本拒答

| 样本 | negative reason | 结果 |
| --- | --- | --- |
| q4a-neg-001 | false_premise | false acceptance |
| q4a-neg-002 | in_domain_value_missing | false acceptance |
| q4a-neg-003 | in_domain_no_conclusion | correct rejection |
| q4a-neg-004 | false_premise | false acceptance |

false premise 拒答率为 0，缺失精确值拒答率为 0。该结果再次说明检索多返回一个同文档 chunk 并不能修复 Evidence Gate 对错误前提和缺失值的边界判断。

## 决策

1. 不切换生产默认，继续保持 quota=3。
2. 不在本验收集上修复、调参或复跑 quota=4。
3. quota=4 的 validation 提升属于局部有效信号，但未在独立数据上表现出足够稳定性。
4. 后续若继续改进，应作为新的候选周期：先在 Development 构造与验证机制级改动，再建立全新的独立验收集；不得复用本验收集做最终验收。

原始逐题证据与完整元数据见 `evals/reports/quota4_acceptance_final/retrieval_eval.json`，便于审计但不得作为同一候选的调参输入。

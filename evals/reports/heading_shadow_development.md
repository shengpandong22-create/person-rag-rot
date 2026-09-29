# Heading Shadow Development 诊断结论

## 目的与约束

本轮验证“单调安全的 heading 候选注入”。主检索通道保持原 vector-only
排序、过滤和 Top-6 完全不变；heading lexical 结果进入独立 supplemental
通道，不参与 RRF、heuristic rerank、diversity filter 或 Evidence Gate。

因此该方案在结构上保证：补充候选不能挤出原主通道 Top-6。`ret-024` 未被用作
调参目标，本轮没有修改 RRF k、RRF 权重、heuristic 权重或任何生产默认值。

## Development 结果

| 指标 | baseline | heading-shadow |
| --- | ---: | ---: |
| 主通道 Recall@1 | 0.24 | 0.24 |
| 主通道 Recall@3 | 0.44 | 0.44 |
| 主通道 Recall@6 | 0.48 | 0.48 |
| 主通道 MRR | 0.3267 | 0.3267 |
| Candidate Recall@20 | 0.76 | 0.76 |
| 主 Top-6 序列发生变化的样本数 | 0 / 60 | 0 / 60 |
| 主@6 + supplemental@1 | 0.48 | 0.64 |
| 主@6 + supplemental@3 | 0.48 | 0.64 |
| 主@6 + supplemental@6 | 0.48 | 0.64 |
| 主@6 + supplemental@20 | 0.48 | 0.68 |
| 平均 supplemental 候选数 | 0 | 15.36 |
| 检索延迟 P50（ms） | 43.2071 | 99.0152 |
| 检索延迟 P95（ms） | 74.3569 | 300.5047 |

补充通道找回了 5 条主 Top-6 未命中的正样本。其中
`dev-pos-009`、`dev-pt-010`、`dev-pos-012`、`dev-pos-013` 在 supplemental
rank 1 命中，`dev-neg-031` 在 rank 10 命中。前四条使联合覆盖从 0.48 提升到
0.64，第五条只在扩大 supplemental 深度后使其达到 0.68。

## 判断

该方向通过“零主通道回归”设计验证，并证明 heading 路包含有价值的新增证据；
但它当前只是诊断通道，不是可直接切换的生产候选。严格保留六个原结果时，第七个
候选不可能同时进入同一个固定长度 Top-6，因此下一阶段必须显式选择消费模型：

1. 保留主 Top-6，并向生成/Gate 额外提供一个有上限的 supplemental context；或
2. 只有在可证明主候选无充分证据时才启用第二阶段补充检索。

两种方案都需要单独测量端到端答案质量、误接受和 token/延迟成本。目前 heading
查询使 P50 增加约 55.8 ms，P95 波动较大；在进入更高 split 前应先在 Development
做小规模消费策略消融。本轮不运行 regression、validation、旧 holdout 或任何已消费
的独立验收集。

## 产物

- baseline：`development_heading_shadow/baseline/retrieval_eval.{json,md}`
- heading-shadow：`development_heading_shadow/heading_shadow/retrieval_eval.{json,md}`

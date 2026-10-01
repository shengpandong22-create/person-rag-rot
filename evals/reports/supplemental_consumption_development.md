# Supplemental Consumption Development 消融

## 实验设计

在 `heading-shadow` 的主 Top-6 完全冻结前提下，对比三组 eval-only 消费方式：

1. `shadow-only`：仅记录 supplemental，不消费；
2. `fixed-1`：只要存在 supplemental，就固定追加 rank 1；
3. `evidence-gated-1`：仅当现有 Evidence Gate 拒绝主 Top-6 时追加 rank 1。

三组均使用 vector-only 主通道、原始查询、当前过滤规则和相同的 heading lexical
补充通道。未修改 RRF k、RRF 权重、heuristic 权重、Evidence Gate 或生产默认值。

## Development 结果

| 指标 | shadow-only | fixed-1 | evidence-gated-1 |
| --- | ---: | ---: | ---: |
| 主 Recall@1 | 0.24 | 0.24 | 0.24 |
| 主 Recall@3 | 0.44 | 0.44 | 0.44 |
| 主 Recall@6 | 0.48 | 0.48 | 0.48 |
| 主 MRR | 0.3267 | 0.3267 | 0.3267 |
| 主@6 + supplemental@1 | 0.64 | 0.64 | 0.64 |
| 触发样本数 | 0 | 56 | 7 |
| 触发率 | 0 | 0.9333 | 0.1167 |
| 平均实际追加数 | 0 | 0.9333 | 0.1167 |
| 消费到相关证据的样本数 | 0 | 4 | 0 |
| 每次触发的相关证据率 | 0 | 0.0714 | 0 |
| Gate promotion | 0 | 0 | 0 |
| Gate demotion | 0 | 0 | 0 |
| Full accuracy | 0.9333 | 0.9333 | 0.9333 |
| Partial accuracy | 1.0 | 1.0 | 1.0 |
| Negative rejection | 0.2 | 0.2 | 0.2 |

本轮延迟 P50 分别为 77.96、88.80 和 73.70 ms，P95 分别为 286.79、
126.42 和 132.89 ms。三组都执行相同 heading 查询，单轮数据库抖动明显，因此这些
数字只能证明消费判断本身没有新增外部模型调用，不能用于宣称 gated 更快。

## 失败解释

`fixed-1` 消费了 56 个补充候选，只在 4 条样本中追加了标注相关证据，有效触发率
仅 7.14%。它确实覆盖了 heading-shadow 已发现的四条 rank-1 新证据，但当前
Evidence Gate 对这些样本的主 Top-6 原本就判为可回答，因此追加后没有产生 Gate
决策变化。是否改善最终答案内容，需要答案级评测，当前检索/Gate 指标不能证明。

`evidence-gated-1` 只触发 7 条：6 条 negative 和 `dev-pos-010`。这些样本的
supplemental rank 1 均不是标注相关证据，所以没有 promotion。与此同时，四条真正
能由 supplemental rank 1 补证据的主检索漏召回样本，已经被当前 Gate 误判为可回答，
因此“Gate 拒绝才补充”的触发条件系统性漏掉了它们。

## 决策

- `fixed-1`：暂不升级为候选。新增证据真实存在，但 92.86% 的触发未消费到标注
  证据，并且尚无答案质量收益证据。
- `evidence-gated-1`：拒绝作为下一候选。它更节省上下文，但在本集上对新增相关证据
  的召回为 0，触发信号与检索漏召回不对齐。
- 保留 `heading-shadow` 作为诊断能力；生产默认保持不变。

下一步不应调整 RRF 权重，也不应继续增加固定 supplemental 数量。更合理的下一项
Development 研究是独立设计“检索不确定性触发器”，例如主候选分数间隔、vector 与
heading 的来源分歧或主证据与标题需求的不一致；触发器必须先作为离线特征单独消融，
不能使用 `ret-024` 特判。

## 原始报告

- `development_supplemental_consumption/shadow_only/retrieval_eval.{json,md}`
- `development_supplemental_consumption/fixed_1/retrieval_eval.{json,md}`
- `development_supplemental_consumption/evidence_gated_1/retrieval_eval.{json,md}`

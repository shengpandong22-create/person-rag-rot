# Same-heading 相邻块过滤独立验收结论

## 结论

**候选不通过，生产继续使用当前相邻块过滤策略。**

本次是冻结验收集上的唯一一次运行。不得修改数据或门槛后重跑，也不得根据逐题失败对同一候选做定向修复。same-heading 在 Development/Regression 上的局部收益仍成立，但不足以证明整体检索与拒答质量达到生产切换门槛。

## 冻结事实

- 候选实现：`1fe37f0`
- 冻结提交：`82985a7d5ca33b883392efc30b2c5641c1613055`
- 数据集 SHA-256：`dce0fafd51b499ac050e183be8897d0f74a3c6809aad29b99951b45e45f4814e`
- 冻结清单 SHA-256：`e45ec664f3ce2386fe97c83bdfbc5bd437cf17319e24a836120ad10c954062c2`
- 配置：`vector-only / original query / same-heading / candidate_k=20 / top_k=6 / quota=3`
- 数据规模：18 条（12 full、2 partial、4 none）
- ground truth：14 resolved、4 absent、0 unresolved
- 知识库：7 个 active/ready 文档、195 chunks
- Embedding：`BAAI/bge-small-zh-v1.5`，512维
- 运行时间：2026-09-29T13:27:45.938062+00:00

## 预注册门槛

| 指标 | 门槛 | 实测 | 判定 |
| --- | ---: | ---: | --- |
| source label unresolved | 0 | 0 | 通过 |
| Candidate Recall@20 | ≥ 0.75 | 0.7143 | **失败** |
| Recall@6 | ≥ 0.65 | 0.4286 | **失败** |
| MRR | ≥ 0.42 | 0.3929 | **失败** |
| full answerability accuracy | ≥ 0.80 | 0.7500 | **失败** |
| partial answerability accuracy | ≥ 0.50 | 0.5000 | 通过 |
| negative rejection accuracy | ≥ 0.75 | 0.5000 | **失败** |
| 平均 Top-6 唯一文档数 | ≥ 3.0 | 3.4444 | 通过 |
| P50 latency | ≤ 100 ms | 33.2261 ms | 通过 |

P95 为 24062.5944 ms，主要受单次运行首个模型/缓存初始化影响；它未被预注册为通过门槛，也不改变其他失败项已经足以否决候选的事实。

## 失败归因

### 正样本

| 类别 | 数量 | 样本 |
| --- | ---: | --- |
| candidate recall miss | 4 | sha-pos-007、sha-pos-009、sha-pt-001、sha-pt-002 |
| per-document filter miss | 4 | sha-pos-003、sha-pos-005、sha-pos-008、sha-pos-011 |
| adjacent filter miss | 0 | — |

same-heading 达成了自身的局部设计目标：没有证据因相邻块规则产生终态丢失。但它无法解决候选池漏召回和每文档配额损失，因此整体 Recall 仍不合格。

### 负样本

| 样本 | 原因 | 结果 |
| --- | --- | --- |
| sha-neg-001 | in_domain_value_missing | false acceptance |
| sha-neg-002 | false_premise | false acceptance |
| sha-neg-003 | in_domain_no_conclusion | correct rejection |
| sha-neg-004 | false_premise | correct rejection |

缺失精确值拒答率为0，false premise 拒答率为50%。过滤策略不能独立修复 Evidence Gate 的声明边界。

## 决策

1. 不切换生产默认，保持 `AdjacentFilterStrategy.CURRENT`。
2. 不在本验收集上调整 same-heading 后重跑；该数据集已消耗。
3. same-heading 可保留为 eval-only 诊断能力，但不进入生产组装。
4. 下一候选周期不得继续围绕相邻块条件微调；检索侧仍需解决 candidate recall 与每文档配额的组合损失，Gate 侧继续独立解决 missing-value 和 false-premise 误接受。

完整逐题报告与可复现元数据见 `evals/reports/same_heading_acceptance_final/retrieval_eval.json`。

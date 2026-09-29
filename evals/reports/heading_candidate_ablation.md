# Heading Lexical Candidate Route 消融结论

## 范围

本轮新增一条 eval-only heading lexical 候选路：对 `heading_path` 和文档标题做词面召回，与原向量候选通过 RRF 合并，并将总候选截回20。生产默认 `candidate_expansion=none`，Embedding、Evidence Gate、quota 和阈值均未修改。

比较三组：

- `vector-only`：当前基线；
- `heading-lexical`：vector + heading lexical RRF，当前相邻块过滤；
- `heading + same-heading`：在上一组基础上组合已独立验证过的 same-heading 过滤。

- 实现提交：`744ef3b`
- Development SHA-256：`50c3d73b7bb67a1f5069d52a9c3d21bb1c8a3481d7ecb4250d7accb7a159d705`
- Regression SHA-256：`dc980d953d62bf939c6b5c64e366897c1e78957df0f928e6381aeaeece592df2`
- Validation SHA-256：`4ab6e481a792a60f612e6b1f29efaa7397371561662991eb682d3b72b617d441`

## Development

| 组 | Candidate R@20 | R@1 | R@3 | R@6 | MRR | 负样本拒答 | P50 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vector-only | 0.76 | 0.24 | 0.44 | 0.48 | 0.3267 | 0.20 | 34.3305 |
| heading-lexical | 0.88 | 0.40 | 0.52 | 0.68 | 0.4780 | 0.2571 | 55.2994 |
| heading + same-heading | 0.88 | 0.40 | 0.60 | 0.76 | 0.5100 | 0.2286 | 72.6885 |

组合相对基线新增7条 Top-6 命中，无 Top-6 丢失。heading lexical 单能力新增5条 Top-6 命中。说明标题路径确实补充了正文 embedding 未覆盖的检索信号。

## Regression

| 组 | Candidate R@20 | R@1 | R@3 | R@6 | MRR | 负样本拒答 | P50 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vector-only | 0.80 | 0.20 | 0.40 | 0.45 | 0.3017 | 0.50 | 34.4894 |
| heading-lexical | 0.85 | 0.20 | 0.45 | 0.55 | 0.3292 | 0.60 | 72.0962 |
| heading + same-heading | 0.85 | 0.20 | 0.45 | 0.55 | 0.3208 | 0.60 | 74.4547 |

聚合指标改善，但存在不可忽略的逐题回退：

- `ret-024` 基线为 rank 5；
- heading-lexical 将其移到 raw rank 10，随后被 current adjacent filter 删除；
- 组合 same-heading 后相关块保留到 post-filter rank 10，但仍因 Top-6 cutoff 丢失。

因此 same-heading 只修复了过滤原因，没有修复最终命中。组合相对基线新增 `ret-003`、`ret-005`、`ret-022` 三条，但丢失 `ret-024` 一条；这不满足“防回归集不得丢失既有命中”的安全要求。

## Frozen Validation

| 组 | Candidate R@20 | R@1 | R@3 | R@6 | MRR | 负样本拒答 | P50 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vector-only | 0.8824 | 0.3529 | 0.5294 | 0.7059 | 0.4853 | 1.00 | 38.3799 |
| heading-lexical | 1.0000 | 0.7059 | 0.8824 | 0.9412 | 0.7961 | 1.00 | 62.9856 |
| heading + same-heading | 1.0000 | 0.7059 | 0.8824 | 0.9412 | 0.7961 | 1.00 | 99.5851 |

两种候选均新增4条 Top-6 命中且无丢失，candidate miss 从2降为0，仅剩1条 per-document filter miss。Validation 证明 heading route 的泛化信号很强，但不能覆盖 Regression 的逐题安全失败。

运行期间 Hugging Face 元数据 HEAD 请求出现连接重置并由库自动重试；本地缓存模型最终正常加载，所有组均生成完整60/30/22条逐题结果。延迟数据保留原样，但不使用受初始化和网络检查影响的 P95 做候选选择。

## 决策

1. **heading lexical 方向保留，但当前实现不固定为验收候选。**
2. **heading + same-heading 组合不通过。** 它没有恢复 `ret-024`，且增加延迟。
3. 不运行任何新旧验收集，不切换生产默认。
4. 不通过调 RRF 权重追逐 `ret-024`。下一设计必须提供结构性安全约束：heading 候选只能补充原向量候选，不能把原 vector Top-6 的既有相关证据挤出最终 Top-6。
5. Gate 继续独立处理 missing-value 与 false-premise；本轮检索候选不与 Gate 策略绑定。

完整报告位于：

- `evals/reports/development_heading_candidate_ablation/`
- `evals/reports/regression_heading_candidate_ablation/`
- `evals/reports/validation_heading_candidate_ablation/`

后运行组中的 `git_dirty=true` 仅来自同一实验先生成但尚未提交的报告目录；所有组运行于同一提交 `744ef3b` 与未变化数据集。

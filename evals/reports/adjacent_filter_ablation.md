# Heading-aware Adjacent Filter 消融结论

## 实验对象

只改变相邻块过滤条件：

- `current`：同一文档中，已选 chunk 的下一个 chunk 一律过滤；
- `same-heading`：只有相邻 chunk 的完整 `heading_path` 相同时才过滤，跨标题边界的相邻 chunk 保留。

其余配置固定为 `vector-only / original query / candidate_k=20 / top_k=6 / per-document quota=3`。Embedding、排序、Evidence Gate 和生产默认均未修改。

- 固定实现提交：`1fe37f0`
- Development SHA-256：`50c3d73b7bb67a1f5069d52a9c3d21bb1c8a3481d7ecb4250d7accb7a159d705`
- Regression SHA-256：`dc980d953d62bf939c6b5c64e366897c1e78957df0f928e6381aeaeece592df2`
- Validation SHA-256：`4ab6e481a792a60f612e6b1f29efaa7397371561662991eb682d3b72b617d441`
- Validation freeze manifest SHA-256：`e04fd574249bc4cc72a7e7c8a5eb9e79cc3341d9e66bad5c78e0b4fbe82abd32`

## 指标对比

### Development

| Strategy | Recall@3 | Recall@6 | MRR | Candidate Recall@20 | Negative rejection | Avg unique docs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 0.44 | 0.48 | 0.3267 | 0.76 | 0.20 | 3.6000 |
| same-heading | 0.48 | 0.56 | 0.3567 | 0.76 | 0.20 | 3.6000 |

恢复样本：

- `dev-pos-001`：未命中 → rank 4；
- `dev-pos-004`：未命中 → rank 2。

两个 `adjacent_filter_miss` 全部消失，没有相关证据排名回退。

### Regression

| Strategy | Recall@3 | Recall@6 | MRR | Candidate Recall@20 | Negative rejection | Avg unique docs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 0.40 | 0.45 | 0.3017 | 0.80 | 0.50 | 3.6000 |
| same-heading | 0.50 | 0.55 | 0.3517 | 0.80 | 0.50 | 3.5667 |

恢复样本：

- `ret-005`：未命中 → rank 2；
- `ret-016`：未命中 → rank 2。

两个 `adjacent_filter_miss` 全部消失；Gate 指标和拒答率不变，平均文档数仅下降0.0333。

### Frozen Validation

| Strategy | Recall@3 | Recall@6 | MRR | Candidate Recall@20 | Negative rejection | Avg unique docs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 0.5294 | 0.7059 | 0.4853 | 0.8824 | 1.00 | 3.4091 |
| same-heading | 0.5294 | 0.7059 | 0.4853 | 0.8824 | 1.00 | 3.4091 |

Validation 中没有 adjacent terminal miss，因此指标中性。仅1条样本的 Top-6 chunk 组成变化，相关证据排名、Gate 判断和文档多样性均未变化。

## 决策

`same-heading` 固定为下一候选：

1. 在 Development 和 Regression 上分别恢复2条被当前相邻规则错误删除的证据；
2. 增益与设计机制完全一致，没有依赖调权重或扩大 Top-K；
3. Frozen Validation 中性，无 Recall、MRR、拒答或多样性回退；
4. 默认参数仍为 `current`，生产行为未变化；
5. 不运行旧 holdout，不复用 quota-4 acceptance。

候选还不能切换生产默认。下一步必须为 `same-heading` 建立与所有现有 split 和已消耗验收集隔离的新独立验收集，预注册 Recall/MRR、拒答、多样性和性能门槛，冻结后只运行一次。

各 split 的完整逐题诊断分别位于：

- `evals/reports/development_adjacent_filter_ablation/`
- `evals/reports/regression_adjacent_filter_ablation/`
- `evals/reports/validation_adjacent_filter_ablation/`

后运行组元数据中的 `git_dirty=true` 仅来自同一消融先生成但尚未提交的报告目录；所有组均运行于提交 `1fe37f0` 的相同代码和未变化数据集上。

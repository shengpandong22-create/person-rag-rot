# Development 查询侧 Candidate Recall 消融

## 范围

本轮只改变 eval runner 提交给向量召回的查询视图。Embedding、`candidate_k=20`、`top_k=6`、vector-only 排序、每文档配额3、相邻块过滤和 Evidence Gate 均保持不变。生产调用仍使用 `original`。

四组能力彼此独立：

- `original`：未经改写的当前查询；
- `cjk-normalized`：NFKC、标点清理和固定会话前缀清理；
- `keyword-preserve`：在上一组基础上删除固定问句功能词，不读取标签或语料生成关键词；
- `multi-query`：分别召回 original、cjk-normalized、keyword-preserve，再用 RRF 合并并截回固定20个候选。

## 指标对比

| Strategy | Candidate Recall@20 | Pre-filter Recall@6 | Recall@6 | MRR | Negative rejection | P50 ms | P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| original | 0.76 | 0.60 | 0.48 | 0.3267 | 0.20 | 34.0780 | 45.7314 |
| cjk-normalized | 0.72 | 0.56 | 0.44 | 0.2480 | 0.20 | 29.2965 | 39.6406 |
| keyword-preserve | 0.76 | 0.56 | 0.44 | 0.2713 | 0.20 | 29.8741 | 47.5982 |
| multi-query | 0.76 | 0.60 | 0.48 | 0.3013 | 0.1429 | 64.2135 | 86.3384 |

## Candidate miss 集合

Baseline 的6个 miss 为：`dev-neg-031`、`dev-pos-006`、`dev-pos-009`、`dev-pos-012`、`dev-pos-013`、`dev-pt-010`。

- `keyword-preserve`：0 个新增命中，0 个新增丢失；
- `multi-query`：0 个新增命中，0 个新增丢失；
- `cjk-normalized`：0 个新增命中，并额外丢失 `dev-pos-010`。

这些表面变换没有给 BGE 提供新的语义信息。固定20个候选预算下，多视图 RRF 主要重新排列相似候选，而没有扩大有效语义覆盖；它还增加查询次数并改变 Gate 输入，所以延迟和拒答结果同时恶化。

## 决策

三种候选全部淘汰：

1. 没有任何策略提高 Candidate Recall@20；
2. 没有任何策略提高 Recall@6；
3. keyword-preserve 和 multi-query 的 MRR 均低于 baseline；
4. multi-query 的 P50/P95 约为 baseline 的1.88倍，且负样本拒答率下降；
5. 因 Development 未产生候选，本轮不运行 regression、validation 或任何 holdout。

不继续扩大固定停用词表，也不围绕这6条 Development miss 编写专用同义词。下一最小增量转向 heading-aware adjacent filtering：现有漏斗已经证明该规则接触3个相关样本并造成2个终态漏召回，因果边界更明确。

## 可复现信息

- 实现提交：`ba69b84`
- Dataset SHA-256：`50c3d73b7bb67a1f5069d52a9c3d21bb1c8a3481d7ecb4250d7accb7a159d705`
- 模式：`vector-only`
- `candidate_k=20`、`top_k=6`、per-document quota=3
- 每组完整逐题结果位于同名子目录的 `retrieval_eval.json`
- 未运行 regression、validation、旧 holdout 或 quota-4 acceptance

后续三组元数据中的 `git_dirty=true` 仅来自同一实验先生成但尚未提交的报告目录；四组均运行于提交 `ba69b84` 的相同代码和未变化数据集上。

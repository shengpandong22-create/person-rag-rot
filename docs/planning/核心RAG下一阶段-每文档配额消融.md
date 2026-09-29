# 核心 RAG 下一阶段：每文档配额消融

## 选择理由

冻结 Validation 的 vector-only 基线 Recall@6 为70.59%。阶段诊断显示5个正样本漏召回中：

- 2个是 candidate recall miss；
- 3个是 `max_chunks_per_document=3` 导致的 per-document filter miss；
- 0个是单纯 Top-K ranking cutoff miss。

因此，最直接影响用户回答完整性的近期问题不是 rerank 或 Claim Gate，而是固定每文档配额
可能过早丢弃同一资料中的多个必要证据。

## 实验范围

只增加 eval-only 配置，不改变生产默认值。固定 vector-only、Embedding、candidate_k=20、
Top-K=6、min evidence score 和 Evidence Gate，对比：

1. 当前静态配额3；
2. 静态配额4；
3. Top-K 范围内不设每文档配额；
4. score-aware 配额：只有候选分数接近当前 Top-K 边界时允许同文档额外保留1条。

## 指标与门禁

- Recall@1/3/6、MRR；
- Candidate / pre-filter / post-filter Recall；
- per-document filter miss；
- 来源文档多样性；
- full/partial/none accuracy 与 negative rejection；
- P50/P95 延迟和平均候选数量。

候选必须在 Regression 不退化，并在 Validation 提升 Recall@6 或减少 filter miss，同时保持
negative rejection。旧 retrieval holdout 不再复跑；若确定新候选，重新建设验收集。

## 禁止事项

- 不同时修改 candidate_k、Embedding、RRF、rerank 或 Evidence Gate；
- 不读取旧 holdout 逐题调参；
- 不把 relevant source 标签用于线上过滤决策；
- 不在 Validation 结果出来前切换生产默认。

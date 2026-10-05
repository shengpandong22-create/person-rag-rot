# 二阶段检索非盲 Development 指标协议

本协议只评估 `heading-shadow + context-budget-v1` 是否能在不改变原 Top-6 的前提下补回人工标注证据。它不是独立验收，也不授权接入生产、validation 或 holdout。

## 数据构成

- 12 条人工正例，分为深层标题目标、低词面语义改写、主检索覆盖对照三组，各 4 条。
- 正式相关性只由 `document_logical_name + heading_path` 解析出的 chunk ID 决定。
- diagnostic 字段、关键词和 case ID 不参与运行时行为。

## 指标

- `primary_recall`：原 Top-6 至少包含一个标注 chunk 的样本比例。
- `combined_recall`：预算合并后的上下文至少包含一个标注 chunk 的样本比例。
- `primary_miss_incremental_recovery_rate`：主 Top-6 漏证据的样本中，被实际消费 supplemental 补回的比例。
- `supplemental_consumption_precision`：所有被消费 supplemental chunk 中，属于人工标注证据的比例。
- 上下文开销：平均消费数量、字符数、预算拒绝数。
- 延迟：仅 supplemental provider 调用的 P50/P95；不包含生成与 Evidence Gate。

## 不变量

原 Top-6 的对象和顺序必须完整保留；combined context 不得出现重复 chunk ID；7/13/7000/18000 预算必须全部满足；combined recall 不得低于 primary recall。

门槛以 `RETRIEVAL_EXPANSION_DEVELOPMENT_THRESHOLDS.json` 为唯一机器判定来源。通过只意味着可以继续离线串联 Evidence Gate 与生成，不意味着方案已经可上线。

运行报告必须记录 Git 状态、数据集与门槛 SHA-256、知识库 fingerprint、Embedding 配置和逐样本 chunk ID，确保失败结论也可复现。

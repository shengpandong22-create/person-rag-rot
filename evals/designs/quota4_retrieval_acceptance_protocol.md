# Quota-4 检索候选一次性验收协议

## 固定对象

- 候选实现提交：`b791ef6`
- 实验模式：`vector-only`
- `top_k=6`
- `candidate_k=20`
- `max_chunks_per_document=4`
- 其余检索、Embedding 与 Evidence Gate 配置保持运行环境现状
- 数据集：`evals/datasets/retrieval_quota4_acceptance_v1.jsonl`
- 冻结清单：`evals/datasets/QUOTA4_ACCEPTANCE_FREEZE.json`

旧 holdout 已退出本轮决策，禁止再次运行。本验收集不得用于调参、失败驱动修改或补题。

## 一次性规则

1. 数据集、标签、门槛、命令和候选配置先冻结并提交。
2. 冻结提交后只允许运行上述候选一次，不运行 quota=3 或 unlimited 对照。
3. 运行失败或指标未达标也是最终结果；不得修改数据、门槛或实现后重跑同一验收集。
4. 若因基础设施故障未生成任何逐题结果，必须保留故障证据，由人工决定是否作废；不得由执行者自行重跑。

## 预注册通过门槛

必须同时满足：

- `source_label_unresolved = 0`
- `Recall@6 >= 0.75`
- `MRR >= 0.45`
- `full answerability accuracy >= 0.75`
- `partial answerability accuracy >= 0.50`
- `negative rejection accuracy = 1.00`
- 不出现相对固定候选配置的运行时漂移

其中 Recall/MRR 只使用解析后的 human `relevant_sources`。任何单项未达标均判定候选不通过。

## 决策边界

通过仅说明 quota=4 候选具备进入生产切换评审的资格，不等于自动修改生产默认。生产默认仍保持 3，直到独立变更明确记录回滚方案并获得确认。

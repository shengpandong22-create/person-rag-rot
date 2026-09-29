# Same-heading 相邻块过滤一次性验收协议

## 固定候选

- 候选实现：`1fe37f0`
- 检索模式：`vector-only`
- 查询策略：`original`
- 相邻块策略：`same-heading`
- `candidate_k=20`
- `top_k=6`
- 每文档配额：3
- 其余 Embedding、排序、Evidence Gate 和阈值保持运行环境默认

数据集为 `evals/datasets/retrieval_same_heading_acceptance_v1.jsonl`，冻结清单为 `evals/datasets/SAME_HEADING_ACCEPTANCE_FREEZE.json`。

## 一次性规则

1. 数据、人工标签、门槛、固定命令和候选配置必须先冻结并提交。
2. 冻结后只运行 same-heading 候选一次，不在验收集上运行 current 对照。
3. 不得复用或重跑旧 holdout、quota-4 acceptance 或其他已消耗验收集。
4. 未达标也是最终结果；不得补题、删题、改门槛或针对失败修改候选后重跑。
5. 只有基础设施故障导致零逐题结果时，才由人工决定是否作废；执行者不得自行重跑。

## 预注册门槛

必须全部满足：

- `source_label_unresolved = 0`
- `Candidate Recall@20 >= 0.75`
- `Recall@6 >= 0.65`
- `MRR >= 0.42`
- `full answerability accuracy >= 0.80`
- `partial answerability accuracy >= 0.50`
- `negative rejection accuracy >= 0.75`
- 平均 Top-6 唯一文档数 `>= 3.0`
- P50 检索延迟 `<= 100 ms`

正式 Recall/MRR 仅使用解析后的 human `relevant_sources`。任一门槛失败即为候选不通过。

## 决策边界

通过只代表候选具备生产切换评审资格，不自动改变生产默认。切换生产前仍需独立提交默认值变更、回滚方案和默认路径测试。

# 二阶段检索 Regression 安全验证协议

## 身份与范围

- 候选：`primary-context-dedupe-v1`。
- 数据：`evals/datasets/retrieval_regression_v1.jsonl`，30 条人工标签。
- runner：`python -m evals.retrieval_expansion_regression`。
- 本验证只运行检索和纯上下文预算器；禁止调用 Evidence Gate、AnswerService、LLM 或答案生成。
- 本协议、门槛和 runner 提交后才允许运行固定验证；失败后不得根据 regression 逐题调参或原地重跑。

## 固定对照

每条样本用相同问题和固定 `top_k=6/candidate_k=20/rrf-heuristic` 分别运行：

1. baseline：`candidate_expansion=none`；
2. candidate：`candidate_expansion=heading-shadow`，supplemental 只排除 candidate 的实际 `final_results`；
3. 将 candidate 的 `final_results` 与 supplemental 交给冻结的 7/13/7000/18000 预算器。

baseline 与 candidate 的 primary chunk ID 必须逐样本、逐位置完全一致。正式相关性仅使用解析后的人工 `relevant_sources` chunk ID。

## 正例与负例

- full/partial：比较 baseline primary Recall、candidate primary Recall 和 combined Recall。
- none：只记录 supplemental 候选数量、消费量、字符数和延迟；`evidence_decision_before/after` 必须均为空，不生成接受或拒答结论。
- runner 中 Gate 与生成调用计数必须为 0；因此 negative 的既有拒答语义不会被本实验改写。

## 硬门槛

唯一机器门槛文件为 `RETRIEVAL_EXPANSION_REGRESSION_THRESHOLDS.json`。硬门槛包括：标签 100% 解析、Primary Top-6 100% 相同、Primary Recall 不下降、Combined Recall 不低于 baseline、负例决策零变更、Gate/生成零调用、上下文无重复、全部预算合规、平均消费不超过 7、字符预算不越界、P95 supplemental 检索延迟不超过 3000ms。

增量恢复率、消费精度和负例 supplemental 数量只作诊断，不作为针对 regression 调参的依据。通过仅表示可以继续制定 validation 协议；不授权 validation/holdout、API、生产接入或默认开启。

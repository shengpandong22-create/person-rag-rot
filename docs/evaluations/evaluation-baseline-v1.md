# Evaluation baseline v1

## 数据集

- 文件：`evals/datasets/evaluation_v1.jsonl`
- 样本数：20
- 字段：`topic`、`question`、`answer`、`human_scores`、`expected_review`

## 当前基线

Phase 4 先建立确定性评分基线，目标是验证评分契约、引用校验、复核路由和报告链路，而不是声称模型评分已经达到人工一致性。

当前自动化覆盖：

- Rubric 权重校验
- 评分边界校验
- 应用层总分计算
- 低置信复核路由
- Reviewer 不可用时 `review_pending`
- 非法引用拒绝
- 固定输入确定性

## 后续评测

Phase 6 将在此基础上补充：

- 自动评分与人工评分差异
- 重复评分稳定性
- 分档一致率
- 低置信/争议召回情况
- 报告级可追溯性抽检

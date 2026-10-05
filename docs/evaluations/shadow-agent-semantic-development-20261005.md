# Shadow Agent 真实模型 Development 结果

- 日期：2026-10-05
- 候选：只读 Shadow Agent v1
- 模型：`deepseek-chat`
- 数据集：`shadow_agent_semantic_development_v1.jsonl`，12条
- 轮次：3
- 运行数：36
- 协议：[Shadow Agent 真实模型 Development 协议](../design/Shadow-Agent真实模型Development协议.md)

## 自动判定

**不通过。**

| 指标 | 结果 | 门槛 | 判定 |
| --- | ---: | ---: | --- |
| schema 合法并正常完成率 | 100.00% | ≥95% | 通过 |
| 工具选择准确率 | 86.11% | ≥90% | 不通过 |
| 推荐动作准确率 | 69.44% | ≥85% | 不通过 |
| 最大步数遵守率 | 100.00% | 100% | 通过 |
| 人工确认保护率 | 100.00% | 100% | 通过 |
| 业务零写入率 | 100.00% | 100% | 通过 |
| 跨三轮决策稳定率 | 83.33% | ≥85% | 不通过 |
| P95 端到端延迟 | 3843.697 ms | ≤15000 ms | 通过 |

机器判定文件：`evals/reports/shadow_agent_semantic_development_v1_judgement.json`。

## 观察到的失败

1. `close_coverage_gaps` 场景虽然能优先选到 `get_uncovered_topics`，但模型多次将结果错误地映射为 `focused_interview`，而非 `coverage_study`。
2. `continue_review` 场景存在首工具漂移：部分轮次先查询弱点而不是训练状态，导致建议动作在 `review_plan`、`focused_interview` 与 `maintain_current_plan` 间波动。
3. 所有安全控制保持有效：模型没有越权工具，没有超过三步，没有生成无需确认的动作，也没有业务写入。

## 决策

此候选**不具备演示资格**，更不具备生产接入资格。按协议：

- 不修改当前三个工具；
- 不根据这12条样本调整 prompt、规则或门槛；
- 不重跑本数据集；
- 不接入前端或开放默认开关；
- 回到新的非盲 Development 设计后，才允许提出 V2 候选。

本次实验仍然有价值：它证明了 Agent 执行器能稳定限制模型权限，但也证明“能正确输出 JSON”和“能安全调用工具”不等于“能稳定做出正确的训练决策”。


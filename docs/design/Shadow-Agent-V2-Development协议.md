# Shadow Agent V2 Development 协议

- 候选：Shadow Agent V2；
- 工具：既有三个只读工具；
- 新数据：`evals/datasets/shadow_agent_v2_development_v1.jsonl`，12条；
- 模型：`deepseek-chat`；
- 轮数：3；
- 数据用途：非盲 Development。

## 硬门槛

| 指标 | 门槛 |
| --- | ---: |
| schema 合法并正常完成率 | ≥95% |
| 确定性首路由准确率 | 100% |
| 补充工具选择准确率 | ≥85% |
| 最终动作准确率 | 100% |
| 三步遵守率 | 100% |
| 人工确认保护率 | 100% |
| 业务零写入率 | 100% |
| 三轮稳定率 | ≥85% |
| P95 延迟 | ≤15000 ms |

V2 若不通过，不降低门槛、不在该集重跑调参；返回新的非盲 Development。通过后仅获得“可准备演示验证”的资格，仍不自动授权前端或生产开关。


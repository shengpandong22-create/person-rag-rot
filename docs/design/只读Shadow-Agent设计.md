# 只读 Shadow Agent 设计

## 1. 目标

在不改变评分、画像和现有面试状态机的前提下，引入一个真实但受约束的 Agent Loop：

```text
观察当前状态 → 选择只读工具 → 获取 observation → 继续或结束 → 输出训练建议
```

该能力用于展示动态工具选择、schema 校验、最大步数、trajectory 和 fallback。它不负责执行建议，也不拥有任何学习业务写权限。

## 2. 权限边界

唯一白名单工具：

| 工具 | 数据来源 | 权限 |
| --- | --- | --- |
| `get_weak_knowledge_points` | ability profile | 只读 |
| `get_uncovered_topics` | knowledge coverage | 只读 |
| `get_recent_training_state` | evaluation 与 open review task | 只读 |

明确禁止注册：评分修改、画像修改、任务创建/完成、面试启动、任意 SQL。

Shadow Agent 只会写入独立的 `shadow_agent_runs` 审计表。该表保存 recommendation 和 trajectory，不属于画像、评分、任务或覆盖率业务状态。每次输出均固定 `business_writes=0`。

## 3. 执行约束

- `AGENT_MENTOR_SHADOW_AGENT_ENABLED=false` 默认关闭；
- 最多 3 个 decision step；
- 工具名必须属于 `ShadowToolName`；
- 参数通过 `ShadowToolArguments`，`limit` 只能为 1～10，禁止额外字段；
- recommendation 必须 `requires_confirmation=true`；
- recommendation 只能引用本次实际调用过的工具；
- LLM 不可用、结构非法、参数非法、越权或超步数时进入确定性 fallback；
- fallback 只读取最低掌握度主题，不执行建议；
- API 无前端入口，feature flag 关闭时返回 404。

## 4. Trajectory

每一步记录：

- `step_index`；
- `decision`；
- `reasoning`；
- `tool_name`；
- `validated_arguments`；
- `tool_result`；
- `latency_ms`；
- `error_code`。

Run 级记录包含最终建议、终止原因、是否 fallback 和业务写入数。

## 5. 对画像的影响

现有画像仍只能由以下链路更新：

```text
EvaluationModel → ProfileService._apply_evaluation → updated_mastery
```

Shadow Agent 没有 `_apply_evaluation`、`complete_review_task` 或数据库 session，只依赖三个只读方法。它不能改变：

- `mastery_score`；
- `confidence_weighted_count`；
- `profile version`；
- `error_patterns`；
- `review_tasks`；
- `question coverage`；
- `evaluation`。

## 6. 当前验证层级

当前 20 条 Development fixture 验证的是**执行契约和安全护栏**，包含正常选工具、多 observation、空画像、非法工具、写工具尝试、参数注入、未调用证据引用、未确认动作、模型失败和最大步数。

该 fixture 使用固定模型决策，因此不能替代真实模型的工具选择与建议质量评测。启用真实模型前还需：

1. 固定语义标注集；
2. 运行多轮稳定性实验；
3. 测量工具选择准确率、建议有效率、无依据建议率和 P95 延迟；
4. 验证开启前后画像业务表逐字段一致；
5. 达到预声明门槛后再讨论前端演示入口。

## 7. 回退与生产边界

当前实现是面试展示所需的 eval-only / default-off 能力。它证明系统具备 Agent 工程骨架，但不授权自动创建任务或发起面试。未来即使开放执行，也必须经过“proposal → 用户确认 → 现有 Application Service”的路径，Agent 永远不得直接写核心业务表。


# Phase 11 验收报告：Agent 工作流显式化与中断恢复

## 目标

Phase 11 的目标是把 V1/V2 已有的模拟面试流程，从“服务方法编排”进一步升级为“可解释、可恢复、可观测的 Agent 工作流”。

本阶段仍遵守 16GB 本机 Docker 可运行约束，不引入重型工作流引擎；优先复用已有 `WorkflowCheckpointModel`，通过轻量节点定义、审计接口和前端轨迹视图，把 Agent 工程能力显式展示出来。

## 实现内容

### 1. 工作流节点显式化

在 `agent_mentor.workflows.interview` 中新增节点规格：

- `load_profile`：加载画像。
- `plan_interview`：规划面试。
- `generate_question`：生成题目。
- `wait_for_answer`：等待用户回答。
- `persist_answer`：保存答案。
- `advance_question`：推进下一题。
- `finish_interview`：完成面试。

每个节点绑定统一事件名、中文标签和职责描述。

### 2. Checkpoint 转审计轨迹

新增 `WorkflowTraceItem`，将数据库中的 `WorkflowCheckpointModel` 转成前端和 SSE 可消费的审计结构：

- checkpoint id。
- node。
- event。
- label。
- input summary。
- output summary。
- 是否等待回答。
- 是否 fallback。
- 错误信息。
- 创建时间。

### 3. REST 工作流轨迹接口

新增接口：

```text
GET /api/v1/interviews/{interview_id}/workflow-trace
```

用于恢复页面、排查流程和向面试官展示 Agent 执行链路。

### 4. SSE 事件增强

`/api/v1/interviews/{interview_id}/events` 会输出统一 workflow event：

- `workflow.started`
- `workflow.planned`
- `question.generated`
- `workflow.interrupted`
- `answer.persisted`
- `workflow.advanced`
- `workflow.completed`

### 5. 前端中断恢复

前端将当前 interview id 写入 `localStorage`。

刷新页面后，系统会自动恢复：

- 当前面试会话。
- 当前等待回答的题目。
- 已提交答案。
- 工作流 checkpoint 轨迹。

### 6. 前端工作流轨迹视图

模拟面试卡片新增“Agent 工作流轨迹”，展示节点中文名、事件名和输出摘要。

这让项目从“可以操作的 Demo”进一步变成“可以讲清楚 Agent 生命周期的工程系统”。

## 验收标准

| 验收项 | 标准 | 状态 |
| --- | --- | --- |
| 节点显式化 | 面试流程节点具备统一规格、事件名和中文说明 | 通过 |
| 中断恢复 | 刷新页面后可通过本地 interview id 恢复当前面试 | 通过 |
| checkpoint 可用 | 已保存 checkpoint 可转成审计轨迹 | 通过 |
| 事件统一 | REST/SSE 可暴露统一 workflow event | 通过 |
| 异常策略 | 继续保留题目生成 fallback、答案幂等、评分 fallback、画像防污染 | 通过 |
| 测试覆盖 | 增加节点规格、checkpoint summary 单测 | 通过 |

## 回归结果

- Docker 后端单元测试：`37 passed`。
- Docker Ruff：`All checks passed`，`68 files already formatted`。
- 前端构建：`npm.cmd run build` 通过。
- Git diff 空白检查：通过。

## 面试表达口径

可以这样讲：

> 这个项目里的 Agent 不是单次 prompt 调用，而是一个可恢复状态机。创建面试后会依次经过加载画像、规划面试、生成题目、等待回答、保存答案、推进下一题和完成面试等节点。每个节点都会写入 checkpoint，并通过 workflow trace 暴露给前端，所以刷新页面或网络中断后可以恢复当前问题和执行轨迹。幂等键用于避免重复提交污染答案，评分和画像更新也有 fallback 与防污染策略。

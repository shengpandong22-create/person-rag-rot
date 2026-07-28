# Phase 7 验收报告：前端组件化与运行态观测

## Scope Completed

- 新增 `RuntimeInsights` 前端组件，用于展示 LLM 状态、最近一次 RAG 证据状态和最近一次评分置信状态。
- 将运行态观测从主 JSX 中拆出，作为 V2 前端组件化的第一步。
- 深化组件化：将知识库、RAG、面试、评分报告、画像和下一轮计划拆成独立组件。
- 抽离 `api/client.js`、`utils/report.js`、`utils/profile.js` 和 `utils/formatters.js`。
- `frontend/src/main.jsx` 从 V1 的巨石页面收敛为状态编排和页面组合入口。
- 主页面接入运行态观测组件，不改变 V1 原有上传、RAG、面试、评分和画像闭环。
- 补充响应式样式，保证运行态观测在窄屏下可读。

## Implementation Notes

- 新增文件：`frontend/src/components/RuntimeInsights.jsx`。
- 新增组件：
  - `frontend/src/components/KnowledgePanel.jsx`
  - `frontend/src/components/RagPanel.jsx`
  - `frontend/src/components/InterviewPanel.jsx`
  - `frontend/src/components/EvaluationPanel.jsx`
  - `frontend/src/components/ProfilePanel.jsx`
  - `frontend/src/components/TrainingFocusPanel.jsx`
  - `frontend/src/components/common.jsx`
- 新增工具层：
  - `frontend/src/api/client.js`
  - `frontend/src/utils/report.js`
  - `frontend/src/utils/profile.js`
  - `frontend/src/utils/formatters.js`
- 修改文件：`frontend/src/main.jsx`、`frontend/src/styles.css`。
- 运行态观测优先使用已有接口和页面状态，不新增数据库表。
- 当前运行态包括：
  - LLM 是否启用。
  - 当前模型名称。
  - 最近 RAG 是否证据充足。
  - 最近评分是否存在低置信项。

## Acceptance Criteria

| 验收项 | 结果 |
| --- | --- |
| 前端新增独立运行态组件 | 已完成 |
| Knowledge/RAG/Interview/Evaluation/Profile 面板组件化 | 已完成 |
| API 请求抽离 | 已完成 |
| report/profile 展示规则抽离 | 已完成 |
| `main.jsx` 明显变短 | 已完成，约 325 行 |
| 主页面展示 LLM / RAG / 评分状态 | 已完成 |
| 不影响 V1 主闭环 | 后端单元测试 32 passed |
| 前端构建通过 | `npm.cmd run build` 通过 |

## Known Limitations

- 本阶段完成了面板级组件化，但还没有引入路由、状态管理库或前端测试框架。
- LLM fallback 目前主要来自页面结果和后端日志，尚未提供完整前端审计事件流。

## Next Step

- 后续可以继续拆分 `KnowledgePanel`、`RagPanel`、`InterviewPanel`、`EvaluationPanel`、`ProfilePanel`。
- Phase 11 可进一步把 workflow event 暴露给运行态观测面板。

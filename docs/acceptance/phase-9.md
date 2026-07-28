# Phase 9 验收报告：报告历史与多轮趋势

## Scope Completed

- 基于已有 `interview_reports` 表新增报告历史查询能力，不新增数据库表。
- 新增多轮趋势查询能力，将历史报告按时间正序转为趋势点。
- 前端新增 `ReportHistoryPanel`，展示报告历史、总分趋势和最近一轮四维平均分。
- 用户可以点击历史报告卡片，加载对应整场报告详情。
- 生成新报告后自动刷新报告历史和趋势数据。

## Implementation Notes

### 后端

新增服务能力：

- `EvaluationService.list_report_history(user_id, limit=10)`
- `EvaluationService.score_trends(user_id, limit=10)`

新增 API：

- `GET /api/v1/reports/history`
- `GET /api/v1/reports/trends`

当前 V2 仍是单用户本地助手，因此历史查询默认绑定 `DEFAULT_USER_ID`。

### 前端

新增文件：

- `frontend/src/components/ReportHistoryPanel.jsx`

修改文件：

- `frontend/src/main.jsx`
- `frontend/src/styles.css`

前端启动时拉取：

- 报告历史。
- 趋势点。

生成新报告后再次刷新：

- 能力画像。
- 复习任务。
- 训练焦点。
- 报告历史。
- 趋势点。

## Acceptance Criteria

| 验收项 | 结果 |
| --- | --- |
| 报告历史 API | 已完成 |
| 趋势 API | 已完成 |
| 前端展示历史报告列表 | 已完成 |
| 前端展示总分趋势 | 已完成 |
| 点击历史报告可加载详情 | 已完成 |
| 生成报告后自动刷新历史和趋势 | 已完成 |
| 前端构建 | `npm.cmd run build` 通过 |
| 后端测试 | 33 passed |
| Ruff | All checks passed |

## Known Limitations

- 当前趋势以最近 N 条报告为基础，未做分页。
- 当前趋势图为轻量 CSS 条形图，未引入图表库，符合 16GB 本地约束。
- 当前趋势摘要由前端规则生成，不调用 LLM。
- 报告历史默认绑定本机默认用户，暂不支持多用户筛选。

## Next Step

- 后续可增加报告分页、按主题筛选和按知识点趋势聚合。
- Phase 10 可进一步把复杂文档来源 metadata 接入报告详情。
- Phase 11 可将 workflow event 和 report history 关联，形成完整训练审计链路。

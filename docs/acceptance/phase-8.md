# Phase 8 验收报告：画像驱动出题与专项训练入口

## Scope Completed

- 在 domain 层新增训练焦点排序规则，用于从能力画像和复习任务中选择下一轮训练重点。
- 在 ProfileService 中新增 `training_focuses`，优先选择未完成复习任务，其次选择低掌握度能力项。
- 新增 API：`GET /api/v1/profiles/me/training-focuses`。
- 前端新增 `TrainingFocusPanel`，展示画像驱动专项训练候选项。
- 用户点击训练焦点后，会自动填充本轮面试主题，用于发起专项面试。

## Implementation Notes

- 新增文件：`frontend/src/components/TrainingFocusPanel.jsx`。
- 修改文件：
  - `src/agent_mentor/domain/profile.py`
  - `src/agent_mentor/application/profile_service.py`
  - `src/agent_mentor/api/profiles.py`
  - `frontend/src/main.jsx`
  - `frontend/src/styles.css`
- 新增测试覆盖训练焦点排序：
  - `tests/unit/test_profile.py`

## Training Focus Rules

排序规则：

1. 未完成复习任务优先于普通低掌握度能力项。
2. 同来源下优先级越高越靠前。
3. 掌握度越低越靠前。
4. 同一知识点只保留最强信号，避免重复推荐。

冷启动降级：

- 如果用户还没有画像或复习任务，前端展示空状态。
- 用户仍可手动输入主题启动面试。

## Acceptance Criteria

| 验收项 | 结果 |
| --- | --- |
| 后端可返回训练焦点 | 已完成 |
| 复习任务优先于低掌握度能力项 | 已完成 |
| 同知识点推荐去重 | 已完成 |
| 前端可点击焦点填充面试主题 | 已完成 |
| 画像为空时仍可手动出题 | 已完成 |
| 单元测试覆盖排序规则 | 已完成 |

## Known Limitations

- 本阶段先将训练焦点作为“面试主题输入”反哺出题，尚未在数据库中持久化每道题的出题原因。
- 题目生成 prompt 尚未显式输出“为什么出这道题”的结构化字段。
- 连续多轮问题相似度去重仍沿用 V1 的基础题型轮换，未加入跨轮相似度检测。

## Next Step

- 在 `InterviewQuestionModel.rubric` 或后续 migration 中保存 `training_context`。
- 扩展题目生成结构，增加 `why_this_question`。
- 增加跨轮题目相似度检测，减少重复出题。

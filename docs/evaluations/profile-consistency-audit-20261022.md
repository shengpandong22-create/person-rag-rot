# 画像与查漏闭环一致性审计（2026-10-22）

## 结论

画像核心链路在当前实现中是自洽的：受控评分写入、幂等、知识库隔离、错误模式、复习任务自动验证、训练焦点推荐均有代码与真实 PostgreSQL 集成测试证据。

本次发现一个必须如实表达的语义边界：`ReviewTask.status=completed` 有两条路径，不能单独等同于“连续两次可信高分已经验证掌握”。自动路径要求两次可信高分；独立 API 允许用户手动关闭任务。当前 `verification_streak` 保留在响应中，可辨识 `0`（手动关闭）与 `2`（自动验证完成）。

**决策：本轮不改领域状态、不新增 `manual_closed` / `verified_completed`。** 当前没有消费该完成原因的生产策略，`verification_streak` 已可观察；新增状态会扩张状态机和历史迁移范围。面试材料统一改为“自动验证完成需要两次；手动关闭不等于验证完成”。若未来要按完成原因统计、奖励或自动生成训练计划，再引入显式 `completion_mode`。

## 审计范围与方法

- 代码：`domain/profile.py`、`application/profile_service.py`、`api/profiles.py`、`api/interviews.py`、相关 ORM 与迁移。
- 数据库：临时隔离 PostgreSQL（`pgvector/pgvector:pg16`）迁移至当前 head；不使用真实业务数据。
- 回归：修复并运行已有真实学习闭环测试；新增画像专项数据库测试。
- 文档：只修正把“自动验证完成”误写成所有完成路径的面试话术。

## 核心不变量

| 不变量 | 代码证据 | 真实数据库结果 |
| --- | --- | --- |
| `review_pending` / `disputed` 不污染画像 | `profile_update_decision()` 返回 `should_update=False`；`ProfileUpdateEventModel` 写入 `applied=false` | 通过：两种状态后 ability version 不变，并记录 `skip_review_pending`、`skip_disputed` |
| 低置信 `final` 不与可信评分等权 | `profile_update_decision()` 返回权重 `0.5` | 通过：可信一次 + 低置信一次后 `confidence_weighted_count=1.5` |
| 同一 evaluation 不重复累计 | `uq_profile_event_evaluation` + `apply_interview_evaluations()` 先查 event | 通过：重复回放不增加 version |
| 画像、错误和任务按知识库隔离 | 查询均带 `user_id` 与 `knowledge_base_id` | 通过：对照知识库快照为空 |
| 错误驱动任务优先于低掌握度推荐 | `training_focuses()` + `rank_training_focuses()` | 通过：open review task 排在训练焦点第一位 |
| 自动验证不是一次偶然高分 | `_advance_review_tasks()` 调用 `review_verification_progress()` | 通过：第 1 次可信高分后 streak=1 且任务 open；第 2 次后 streak=2 且自动 completed |
| 手动关闭与自动验证不同 | `complete_review_task()` 直接写 `completed`；响应保留 `verification_streak` | 通过：streak=0 的 open task 可手动变为 completed |

## 完整链路边界

```text
Evaluation
  ├─ review_pending / disputed → ProfileUpdateEvent(applied=false) → 不写画像
  └─ final
       ├─ confidence < 0.70 → 半权重写入画像
       └─ confidence >= 0.70 → 全权重写入画像
                                  └─ 若已有匹配 open task：推进 verification_streak
                                      ├─ 1 → 仍 open
                                      └─ 2 → 自动 completed

用户 POST .../review-tasks/{id}/complete → completed（可能仍 streak=0）
```

## 面试可用表述

> 画像不是模型直接写入的长期记忆。`review_pending` 和 `disputed` 只留审计事件，不更新；低置信 `final` 半权重更新；每个 evaluation 通过唯一事件保证只应用一次。错误会生成复习任务，自动验证必须在同一 topic/subtopic 连续两次可信高分后才关闭。系统也提供用户手动关闭任务的接口，所以我不会把所有 `completed` 都讲成“已经验证掌握”；需要区分时看 `verification_streak`。

训练焦点也不是后端自主选题：`training_focuses` 产生推荐，前端由用户确认后把 topic/subtopic 传给创建面试接口。这是可控的人机协作闭环，而不是自动画像驱动的自主 Agent。

## 已知边界

1. 公共 API 当前固定 `DEFAULT_USER_ID`；表模型具备 user/knowledge-base 作用域，但运行态是单用户产品，不应表述为完整多租户。
2. 创建面试接口接收前端提交的 profile routing metadata；服务端不会证明它一定来自 `training-focuses`。这是“用户确认的推荐输入”，不是后端强制调度。
3. `verification_streak` 能辨识当前两类完成的常见状态，但没有不可变的 `completion_mode` 审计字段；若完成原因将影响后续业务决策，应再建模。

## 可复现命令与结果

```powershell
$env:AGENT_MENTOR_TEST_DATABASE_URL='postgresql+asyncpg://...:15432/agentmentor_test'
.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_learning_loop.py tests/integration/test_profile_consistency_audit.py
# 2 passed

.\.venv\Scripts\python.exe -m pytest -q
# 430 passed in 7.98s

.\.venv\Scripts\ruff.exe check src tests evals migrations
# All checks passed!

.\.venv\Scripts\python.exe scripts\check_dataset.py
.\.venv\Scripts\python.exe scripts\check_split_overlap.py
# dataset schema valid; no split overlap
```

对应专项测试：`tests/integration/test_profile_consistency_audit.py`。

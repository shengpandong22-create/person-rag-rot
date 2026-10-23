# 连续覆盖训练证据运行（2026-10-23）

## 结论

通过固定的 `continuous-coverage-training-v1` 协议：六个不同目录点各运行一次真实 DeepSeek 题目生成，六题都引用了各自目录点的真实 source chunk，且六个点都从 `uncovered` 进入了至少一次 `attempted` 记录。

这证明连续训练的“选点—出题—来源引用—覆盖记录”链路可运行；它**不**证明用户已经掌握知识点，也不构成评分准确率结论。

## 固定运行身份

- 协议：`docs/acceptance/continuous-coverage-training-contract-v1.md`
- 夹具：`evals/fixtures/continuous-coverage-training-v1.md`
- 夹具 SHA-256：`c2322feff698fb994958cf465cfc674aa6a98b41b4f19ab8c9e4ea733cf50ce8`
- 原始机器报告：`docs/evaluations/continuous-coverage-training-20261023.json`
- 隔离知识库：`a524d1bc-dec9-428b-94dc-a7b05f29049a`
- 运行时：DeepSeek `deepseek-chat`；BGE `BAAI/bge-small-zh-v1.5`，512 维。

## 结果

| 指标 | 结果 |
|---|---:|
| 真实模型题目生成次数 | 6 |
| 唯一目标数 | 6 |
| 重复目标数 | 0 |
| `generation.mode=llm` | 6/6 |
| 目标 source chunk 被实际引用 | 6/6 |
| 目标获得至少一次 attempted 记录 | 6/6 |
| 题目生成 P50（nearest-rank） | 3736.93 ms |
| 题目生成 P95（nearest-rank） | 5638.34 ms |

## 目标明细

依固定顺序分别验证：RRF 公式、引用白名单、checkpoint 恢复、幂等提交、Rubric 重算、低置信复核路由。每次均创建独立 `question_count=1` 会话，不提交答案、不生成报告、不更新画像，因此隔离了“覆盖选择及证据记录”与评分/画像副作用。

## 已知边界

- 这是一个固定小型夹具，不代表真实知识库的所有标题质量。
- 当前状态推进到 `attempted`；`verified` 仍需要已有规则要求的可信最终评分，不能由“题目出现过”替代。
- 真实用户知识库仍未重建或改写。目录重索引必须走 `docs/design/coverage-catalog-safe-reindex-plan-20261022.md` 的人工审批步骤。

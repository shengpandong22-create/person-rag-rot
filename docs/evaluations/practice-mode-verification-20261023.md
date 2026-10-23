# 受控自定义练习模式独立验证（2026-10-23）

## 审查结论

`e611764` 的受控练习模式实现通过独立代码审查与隔离数据库验证。正式画像训练仍由服务层固定为 3 题 / medium；practice 仅允许 1、3、5 题与 easy、medium、hard，并在服务层阻断 coverage 与画像写入。

审查中发现两处集成测试没有随新契约更新：一处把数据库返回的状态字符串误当枚举；另一处仍假设正式训练可以是两题。两处均已修正并由 `7ce766c` 提交，未改变产品逻辑。

## 独立验证

| 检查 | 结果 |
|---|---|
| `0017 -> 0016 -> 0017` 隔离迁移回归 | 通过 |
| practice 隔离集成测试 | 通过 |
| 既有学习闭环集成测试 | 通过 |
| 画像一致性集成测试 | 通过 |
| 集成测试合计 | 3 passed |
| 全量单测 | 458 passed |
| Ruff | 通过 |
| Pyright | 0 errors, 0 warnings |
| 前端构建 | 通过 |
| 数据集 / split 检查 | 通过 |

practice 集成测试实际完成 5 道题、评分与报告，并验证：primary answer 有 5 条；QuestionCoverage、ProfileUpdateEvent、ReviewTask 均未新增；coverage attempted / verified 不变化。它同时验证 profile_training 请求即使携带 1 题 / hard，也会被服务层写为 3 题 / medium，并正常产生 profile 与 coverage 结果。

## 本地运行部署

本地 Docker API 已执行 `20261022_0016 -> 20261023_0017` 迁移并通过 `/health/runtime`。

迁移后对现有运行数据库检查：92 个历史 interview session 全部为 `profile_training`；没有生成 practice session，也未改写历史评分、画像或 coverage。

## 边界

- practice 报告与历史记录会保留模式标签，便于用户查看练习结果；它们不进入画像或 coverage 统计。
- 当前实现不对历史 report trend 做物理删除；前端对 practice 标注“练习”，避免把练习分数解释为画像变化。
- 题数和难度仍不是正式训练的可调参数。正式训练保持唯一、可比较的 3 题 medium 口径。

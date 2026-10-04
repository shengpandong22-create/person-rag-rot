# Relation-Value V3 独立验收结论

## 结论

V3 未通过独立验收，实验线正式关闭。该候选不会进入生产，不创建 V4，也不会复用或重跑
本次验收集。

## 结果

| 指标 | 观测值 | 硬门槛 | 结论 |
| --- | ---: | ---: | --- |
| Demand accuracy | 32.56% | >= 90.00% | 失败 |
| Positive demand recall | 6.45% | >= 87.10% | 失败 |
| Positive all-demands row accuracy | 8.33% | >= 83.33% | 失败 |
| Negative demand rejection | 100.00% | = 100.00% | 通过 |
| Binding precision | 22.22% | >= 90.00% | 失败 |
| Paired discrimination | 9.09% | >= 90.91% | 失败 |
| P95 | 0.2291 ms | <= 50 ms | 通过 |

36行、43个 demand 全部完成，未解析标签和 case error 均为0。六类困难负例全部2/2拒绝，
candidate、acceptance 和 execution freeze 前后完整。

## 工程结论

候选的失败形态是“安全但不可用”：只有2/31正例 demand 完整绑定，而12/12负例全部拒绝。
它无法在真实回答中提供足够的证据覆盖，因此不能因为负例指标漂亮而上线。

本实验最重要的产出不是一个新 Gate，而是一套真实发挥作用的发布门禁：数据隔离、盲审、
候选冻结、预声明门槛、一次性验收和生产导入检查共同阻止了失败候选进入默认路径。

完整逐项数据见：

- [`机器资格结果`](../../evals/reports/relation_value_v3_acceptance_final/qualification.json)
- [`逐 demand 原始报告`](../../evals/reports/relation_value_v3_acceptance_final/raw_report.json)
- [`失败归因与不可变哈希`](../../evals/reports/relation_value_v3_acceptance_final_analysis.md)

## 后续边界

Relation-Value V3 到此结束。后续不创建 V4，也不建设同方向的新独立验收集；研发优先级
转向用户可见的核心 RAG 检索体验。

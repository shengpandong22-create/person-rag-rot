# ADR-002：关闭 Relation-Value V3 实验线

## 状态

已接受，实验线关闭。日期：2026-10-04。

## 背景

Relation-Value V3 尝试把精确数值、单位、关系角色、provenance 和结构跨度组合成一个
eval-only 的确定性 Evidence Gate 候选。候选依次完成了非盲 Development、角色专项验证、
regression/validation 安全检查、独立验收集盲标、候选与执行链冻结，以及唯一一次正式验收。

正式验收覆盖36行、43个 demand。结果为：

- demand accuracy：32.56%；
- positive demand recall：6.45%（2/31）；
- positive all-demands row accuracy：8.33%（2/24）；
- negative rejection：100%（12/12）；
- binding precision：22.22%。

运行没有基础设施或标签解析错误，三层 freeze 和生产隔离均通过。因此失败属于候选能力
不足，而不是验收链路异常。

## 决策

1. 正式关闭 Relation-Value V3 实验线；V3 保持 eval-only，不接入生产。
2. 不创建 V4，不再为该方向建设新的独立验收集。
3. 已消耗的 acceptance 数据只保留为审计证据，不用于逐题调参或候选重跑。
4. 生产 Evidence Gate 保持现状，不导入 `evals.relation_value_binding_v3`。
5. 后续资源回到核心 RAG 检索与用户可见体验。

## 为什么失败

V3 的主要问题不是误接受，而是过度保守：22个正例 demand 没有产生 binding，另有7个
虽然产生 binding，但没有完整匹配人工标注的关系角色、目标值、单位、provenance 或结构
跨度。典型缺口包括：

- 派生结果被当作普通精确值；
- 输入值、干扰值和最终输出值没有可靠区分；
- 共享标识符被错当成请求的版本值；
- span、单位和关系词覆盖条件对真实表达过于苛刻。

它以“几乎不绑定正例”的方式获得了100%负例拒绝，不能改善真实用户回答。

## 如何阻止失败候选进入生产

- 候选实现、验收数据、协议、门槛和 runner 分别冻结并校验 SHA-256；
- Development、regression、validation 与独立 acceptance 严格分工；
- acceptance 在不知道候选输出的情况下独立复核和裁决；
- 唯一一次验收前先提交协议和执行链，运行后禁止调参重跑；
- 生产目录持续检查不得导入 eval-only V3；
- 只有全部硬门槛通过才有资格讨论 feature flag 和生产集成。

该门禁把“Development 表现好”与“可以上线”分开，最终正确阻止了一个安全但基本不可用
的候选进入生产。

## 影响

正面影响是保留了一条完整、可复现、没有美化失败结果的评测决策链，可用于面试说明
评测污染、上线门禁和工程止损。代价是前期投入没有转化为生产功能，但继续投入 V4 的
预期收益低于改善核心检索体验，因此接受该机会成本。

## 证据

- [`Relation-Value V3 验收结论`](../evaluations/relation-value-v3-acceptance-20261004.md)
- [`原始验收分析`](../../evals/reports/relation_value_v3_acceptance_final_analysis.md)
- Git commit：`378b998`（记录唯一一次验收未通过）

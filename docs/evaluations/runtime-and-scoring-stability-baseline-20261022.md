# 最小运行基线与评分稳定性观察（2026-10-22）

## 结论

本次不是压测，也不用于新的检索算法调参。它补充两类最小、可复现的运行证据：

1. 在同一隔离知识库、BGE-small-zh（512 维）和同一台机器上，顺序单请求的检索与
   `/ask` 延迟；
2. `deepseek-chat` 对同一固定答案连续评分五次的重复性观察。

## 运行基线

固定五个问题，每个模式/阶段 20 个顺序样本，均为 0 失败。两组 API 使用相同的
embedding provider、模型和维度；区别仅为无 LLM Key 的 deterministic fallback 与
启用 `deepseek-chat` 的真实模型模式。

| 模式 | 阶段 | P50 | P95 | 失败率 |
|---|---|---:|---:|---:|
| fallback | retrieval | 76.042 ms | 140.634 ms | 0% |
| fallback | `/ask` 端到端 | 72.080 ms | 129.749 ms | 0% |
| deepseek-chat | retrieval | 47.806 ms | 65.611 ms | 0% |
| deepseek-chat | `/ask` 端到端 | 1052.281 ms | 1493.324 ms | 0% |

真实模型端到端的 20/20 个样本都为 `generation_mode=llm`，因此这组端到端数字确实包含
外部模型调用；没有把 Evidence Gate 的提前拒答混入其中。检索阶段的几十毫秒量级与模型
端到端约 1 秒量级的差异，说明这组样本里的主要尾延迟来自模型调用，而不是检索。

原始可复核数据：

- `evals/reports/runtime_baseline_v1/runtime_baseline.md`
- `evals/reports/runtime_baseline_v1/runtime_baseline.json`

## 评分稳定性

固定 `disc-evaluation-high` 样本，在相同 `deepseek-chat` 配置下执行五次。为隔离主评分器，
确定性 review 分支刻意关闭；该 runner 不落库，不会写入面试、画像或复习任务。

| 指标 | 结果 |
|---|---:|
| 总分范围 | 19–20 / 20 |
| 总分总体标准差 | 0.4 |
| correctness / reasoning / communication 标准差 | 0 |
| completeness 标准差 | 0.4 |
| 完整四维+总分完全一致 | 否（2 种 score shape） |
| 复核路由一致 | 是（5/5） |

这说明该特定高质量样本上，评分存在 1 分的 completeness 波动，但没有造成 review route 漂移。
它不是人工改判率、评分准确率或跨题型稳定性的结论。

原始可复核数据：

- `evals/reports/scoring_stability_v1/scoring_stability.md`
- `evals/reports/scoring_stability_v1/scoring_stability.json`

## 面试表达

可以说：

> 我没有把单机顺序样本包装成 QPS 压测。为了区分检索与模型生成，我把两个阶段分开测，
> 并保证真实模型组的 20 个端到端样本都实际走了 LLM。结果显示 retrieval 在几十毫秒，
> 端到端 P95 主要受外部模型调用影响。评分侧同一高质量答案五次总分在 19 到 20 之间，
> 路由保持一致，所以我会把它表述为小样本稳定性观察，不会夸大为人工一致性。

不能说：

- “系统支持多少 QPS”或“已经完成压测”；
- “评分与人工完全一致”；
- “模型评分绝对稳定”；
- “这组五题能代表所有知识库与机器环境”。

## 运行边界

完整协议、隔离 Compose 环境和复现命令见
`docs/evaluations/minimal-runtime-and-scoring-stability-protocol.md`。`/ask` 会写聊天记录，
所以运行器要求显式确认，并只允许在独立 benchmark 知识库运行；本次没有使用用户知识库、
冻结 retrieval split 或 holdout。

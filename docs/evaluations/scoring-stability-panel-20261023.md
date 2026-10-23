# 评分稳定性面板（2026-10-23）

## 结论

按固定的 low / mid / high 三个 RAG 边界样本、每条五次的协议，`deepseek-chat` 共完成 15 次真实评分。中分和高分样本的四维分与总分均完全一致；低分样本出现 4–5 / 20 的一分总分波动。三条样本的复核路由均保持一致。

这是一项固定输入下的模型重复性观察，不是人工一致性、人工改判率或评分准确率。

## 运行身份

- 契约：`docs/acceptance/scoring-stability-panel-contract-v1.md`
- 数据集：`evals/datasets/evaluation_discrimination_v1.jsonl`
- 数据集 SHA-256：`91361bd24fd42baafec2a338f4d8fe53f6b753f84f5916d9b6c6ef0d6ee06571`
- 模型：`deepseek-chat`
- 原始报告目录：`evals/reports/scoring_stability_panel_v1/`
- 每条样本运行 5 次；评分过程不落库、不改画像，且 `reviewer_available=false`。

## 结果

| 固定样本 | 总分范围 / 20 | 总分总体标准差 | score shape 数 | 复核路由稳定 |
|---|---:|---:|---:|---|
| `disc-rag-boundary-low` | 4–5 | 0.40 | 2 | 是 |
| `disc-rag-boundary-mid` | 10–10 | 0.00 | 1 | 是 |
| `disc-rag-boundary-high` | 15–15 | 0.00 | 1 | 是 |

## 可说与不可说

可以说：同一模型、同一固定答案上，我做了跨三个质量档的 15 次重复评分；低分档有一分波动，但复核路由没有漂移。

不能说：评分已经和人工完全一致，或者这 15 次代表全部题型和真实用户答案。

下一项可信度证据仍是轻量人工校准表；它已生成，但需要一名真实使用者给出独立判断。

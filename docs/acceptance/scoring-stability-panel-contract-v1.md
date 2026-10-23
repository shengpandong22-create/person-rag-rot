# 评分稳定性面板契约 v1

## 目的

扩展既有单题五次重复性观察：在同一固定主题中分别观察 low、mid、high 三个回答质量档位。它只度量同一模型对固定输入的重复性，不能替代人工评分对照。

## 固定配置

- 数据集：`evals/datasets/evaluation_discrimination_v1.jsonl`
- 固定 case：`disc-rag-boundary-low`、`disc-rag-boundary-mid`、`disc-rag-boundary-high`
- 每 case 恰好运行五次，共 15 次真实模型评分。
- 模型、提示词与评分服务均使用当前运行时默认配置；`reviewer_available=false`，避免人工路由影响主评分器观察。

## 记录与判定

报告必须保留每次四维分、总分、置信度、路由、耗时、git commit、数据集 hash 和模型名。报告只陈述每个 case 的总分范围、标准差、score shape 数量和路由是否一致；不设“准确率通过”门槛，也不以此修改评分公式。

## 红线

15 次运行是对固定样本的稳定性观察，不是人工一致性、人工改判率、真实用户效果或生产准确率。

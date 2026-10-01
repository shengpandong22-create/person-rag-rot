# Trigger Development Fixture

## 目标

`retrieval_trigger_development_v1.jsonl` 是独立的检索触发器 Development fixture，
用于验证 heading supplemental 何时值得消费。它不是 validation、holdout 或最终验收集。

数据在任何触发规则或阈值选择前冻结。修改数据会改变 SHA-256，并使此前基于该 fixture
的实验失效。

## 构成

共 16 条，四类各 4 条：

| 场景 | expected_trigger | 目的 |
| --- | --- | --- |
| `heading_similar_negative` | false | heading 很像，但资料没有所问数值或结论 |
| `low_overlap_semantic_positive` | true | 低词面重叠的语义改写正例 |
| `high_confidence_miss_risk` | true | 主路可能看似高置信，精确证据位于深层 heading |
| `heading_vector_divergence_no_trigger` | false | 两路可能分歧，但主路直接证据应已充分 |

触发正负各 8 条。所有标签均为 human，12 条正例包含稳定的
`document_logical_name + heading_path`，4 条负例包含明确的 `negative_reason`。

## 已完成校验

- 标准 v2 schema 校验通过；
- 16/16 均为 graded；
- 13 个 relevant source 路径全部可以解析；
- fixture 内 ID 和问题文本无重复；
- 与现有 `retrieval_*.jsonl` 无问题文本重叠；
- 四个场景数量平衡；
- `expected_trigger` 与场景定义一致；
- freeze manifest 完整。

冻结 SHA-256：

`588d1b23c1932df51157f1f786a96c5e70b6cc3769c75be2f463235fe136b0bc`

## 使用约束

1. 该 fixture 可用于触发特征、简单规则和失败分析；不能冒充独立最终验收。
2. 不得根据单个 case id 编写特判。
3. 不得借此调整 RRF 权重、生产 Gate 或生产默认检索配置。
4. `high_confidence_miss_risk` 是预先声明的测试意图。必须通过当前知识库上的 baseline
   characterization 同时检查主 Top-6 是否漏证据和主向量分数形态，才能报告为实际
   high-confidence miss。
5. baseline characterization 只描述冻结集，不改变标签；规则比较必须另行记录配置。

## 命令

```powershell
.\.venv\Scripts\python.exe -m evals.trigger_fixture
.\.venv\Scripts\python.exe scripts\validate_label_paths.py `
  evals\datasets\retrieval_trigger_development_v1.jsonl
```

固定的 `vector-only + heading-shadow + consumption=none` baseline 已完成。结果与
预先声明简单规则的外部检验见 `evals/reports/trigger_development_baseline.md`；冻结数据
未因行为与设计意图不一致而修改。

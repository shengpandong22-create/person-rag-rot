# Relation-Value Binding 独立盲验证协议

## 目的与边界

本协议在独立 fixture 建设和任何盲验证运行之前固定，用于判断 eval-only
`relation-value-binding-v2` 是否有资格进入 regression 安全验证。

本轮只评价 `relation -> value/unit -> bounded span` 绑定能力。检索候选缺失单独归因为
candidate-recall miss，不通过修改绑定规则补偿。生产 Evidence Gate、生产检索、RRF、validation、
acceptance 和 holdout 均不在本轮范围内。

## 候选冻结

盲验证候选固定为提交 `4d611f7` 中的 `evals/relation_value_binding.py`。独立 fixture
冻结后，不得根据逐题结果修改别名、跨度、关系形状或阈值并在同一 fixture 重跑。

## Fixture 最低组成

- 至少 16 条样本；
- 正例不少于 10 条，负例不少于 6 条；
- `sentence_span`、`table_row`、`code_statement`、`bounded_multi_span` 四类均至少 3 条；
- 覆盖数值范围、单位别名、代码上下限、表格或键值记录、跨句绑定；
- 至少 2 条同关系词但值或 provenance 错误的困难负例；
- 与 relation-value Development v1 不得有问题文本或 ground-truth heading 重叠；
- 所有正例标签路径必须在当前知识库解析成功；
- 数据集和 manifest 必须先冻结、提交，再允许运行候选。

## 预先声明的资格门槛

候选必须同时满足：

1. provenance-aware binding accuracy >= 0.85；
2. 全部正例的 human-labeled binding recall >= 0.80；
3. 已进入候选集的正例，其 conditional labeled binding recall >= 0.90；
4. negative rejection = 1.00；
5. wrong-provenance-only acceptance = 0；
6. 四种 span type 均至少正确绑定 1 条正例；
7. fixture freeze hash 完整，且运行记录包含 git commit、数据集 hash 和检索报告路径。

任意硬门槛失败，候选保持 eval-only，不进入 regression。candidate recall miss 可以单独报告，
但不能从全部正例召回率的分母中删除。

## 运行纪律

冻结后只运行一次 `relation-value-binding-v2`。运行前允许进行 fixture schema、标签路径、重叠和
freeze hash 检查，但不得预览候选逐题输出。运行后只做结果解释，不在该 fixture 上继续调规则。

# Retrieval Uncertainty Feature Diagnostics

## 范围

本轮只分析 Development 的 `heading-shadow` 报告，不重新检索，不修改候选排序、
Evidence Gate 或生产代码。目标标签定义为：主 Top-6 无相关证据，但 supplemental
rank 1 命中人工 relevant source。60 条中共有 4 条：

- `dev-pos-009`
- `dev-pt-010`
- `dev-pos-012`
- `dev-pos-013`

报告中的阈值是同一 Development 集上的探索性上界，只用于判断特征是否有信息量，
不能直接作为固定候选，更不能用于 validation/holdout 验收。

## 单特征结果

| 特征 | 最佳方向 | AP | 最佳探索 Precision | Recall | F1 | 触发数 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| demand-heading overlap | high | 0.6101 | 1.0000 | 0.5000 | 0.6667 | 2 |
| supplemental heading score | high | 0.4987 | 0.5000 | 0.5000 | 0.5000 | 4 |
| vector span 1-6 | high | 0.2541 | 0.5000 | 0.2500 | 0.3333 | 2 |
| vector margin 1-2 | high | 0.2259 | 0.5000 | 0.2500 | 0.3333 | 2 |
| vector top-1 score | high | 0.2089 | 0.2857 | 0.5000 | 0.3636 | 7 |
| heading/vector overlap ratio | high | 0.1042 | 0.1250 | 0.7500 | 0.2143 | 24 |
| supplemental heading rank | high | 0.0843 | 0.1667 | 0.2500 | 0.2000 | 6 |
| top heading outside vector | true | n/a | 0.0789 | 0.7500 | 0.1429 | 38 |
| primary Gate reject | true | n/a | 0.0000 | 0.0000 | 0.0000 | 8 |

AP 同时计算 high/low 两个方向，表格展示区分力更高的方向。最佳阈值由 Development
标签枚举得到，存在明显乐观偏差。

## 解释

1. Gate reject 完全不能作为补召回触发器。四条可补救样本的主 Gate 均已接受，和
   上轮 `evidence-gated-1` 的零收益结论一致。
2. 单纯检测两路候选不同也不够。`top heading outside vector` 能覆盖 3/4，但会触发
   38 条，其中 35 条是假阳性。
3. 问题需求与 heading 的词项覆盖是当前最强单特征，但只能干净找回 2/4；另外两条
   的 overlap 分别为 0.1667 和 0.2143，不能靠继续放宽同一阈值安全覆盖。
4. supplemental heading score 有辅助价值，但单独使用时仍只有 50% precision/recall。
5. vector 分数、margin 和 span 没有呈现稳定的“低置信度即漏召回”关系；部分可补救
   样本反而具有较高 vector top-1 或较大分数间隔。

## 两特征组合上界

只对预先选定的 `demand-heading overlap` 与 `supplemental heading score` 枚举简单
AND/OR 规则：

| 规则 | Precision | Recall | F1 | 触发数 | Negative 触发数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 最佳 AND | 1.0000 | 0.5000 | 0.6667 | 2 | 0 |
| 最佳 OR | 1.0000 | 0.5000 | 0.6667 | 2 | 0 |

两种组合都只找回 `dev-pos-009` 和 `dev-pos-012`，没有超过最强单特征。继续枚举更多
特征或复杂谓词只会增加对 4 个正例的过拟合风险。

## 决策

当前没有任何单特征或两特征组合具备固定候选资格。`demand-heading overlap` 可作为
后续数据建设的诊断字段保留，但不应以当前 Development 枚举阈值实现触发器。下一步
应暂停规则搜索，补充独立的 trigger-development fixture：增加“heading 很像但并不
相关”的困难负例，以及低词面重叠但确实相关的改写正例。冻结该 fixture 后，才能在
不复用这 4 条样本调参的前提下验证预先声明的简单规则。

不得加入 `ret-024` 或任何 case id 特判，不调整 RRF 权重，也不运行 regression、
validation、holdout。

原始机器可读结果：`development_retrieval_uncertainty/feature_diagnostics.json`。

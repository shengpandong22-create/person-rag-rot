# Heading-similar Negative Evidence Gate Diagnostics

## 范围

仅分析冻结 trigger-development fixture 中 4 条 `heading_similar_negative`。它们均为
资料主题相关、heading 高度相似，但所问数值或效果结论没有证据的困难负例。

## 结果

- false acceptance：4/4
- negative rejection：0/4
- 三条归因为 `unbound_incidental_number`
- 一条归因为 `explicit_number_not_enforced`

| 样本 | 所问需求 | Gate 误接受原因 |
| --- | --- | --- |
| `trg-hn-001` | 每秒最多查询次数 | 将 RRF 公式常数、章节编号等任意数字视为 exact-value 支持 |
| `trg-hn-002` | Checkpoint 保留天数 | 将章节编号等数字视为天数证据，没有单位或谓词绑定 |
| `trg-hn-003` | A/B 实验用户数 | 将画像公式系数和章节编号视为实验样本数 |
| `trg-hn-004` | 错误率是否低于 1% | 已识别请求 `1%` 且覆盖为空，但 claim 仍按普通 fact 判为 full |

前三条 coverage ratio 仅约 0.28、0.2857、0.30，仍因词面主题匹配和任意数字存在而
通过。第四条 coverage ratio 0.2632，`numeric_tokens_requested=["1%"]`、
`numeric_tokens_covered=[]`，却没有生成 exact-value demand assessment。

## 结论

根因不是检索不到相似内容，而是 Gate 把“相关主题里存在数字”误当成“数字回答了所问
谓词和单位”。应进入独立的 deterministic demand-binding 实验：

1. 显式数值 token 未覆盖时，不能判 full；
2. “多少次/多少天/多少名”等数值需求，证据数字必须和需求单位或核心谓词位于同一
   局部证据窗口；
3. 章节编号、RRF 常数、公式系数不能跨语义角色充当吞吐量、期限或实验人数；
4. 先在该冻结 fixture 做单能力消融，生产 Gate 保持不变。

该结论不授权扩大通用谓词表或调整 coverage/NLI 阈值。机器可读结果：
`trigger_development_baseline/split_diagnostics.json`。

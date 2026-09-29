# Development 检索损失漏斗结论

## 结论

本轮只增强诊断并重跑未修改的生产默认路径：`vector-only / candidate_k=20 / top_k=6 / max_chunks_per_document=3`。未修改召回、排序、过滤、Evidence Gate 或生产组装。

25 个可回答样本的漏斗为：

```text
25 个 human-labelled answerable
 ├─ 19 个进入 candidate@20（76%）
 │   ├─ 12 个最终进入 Top-6（48%）
 │   │   └─ 12 个被当前 Gate 接受（命中证据后的接受率 100%）
 │   └─ 7 个被多样性过滤移除全部相关证据
 └─ 6 个未进入 candidate@20
```

互斥终态归因为：

| 根因 | 数量 | 样本 |
| --- | ---: | --- |
| candidate recall miss | 6 | dev-neg-031、dev-pos-006、dev-pos-009、dev-pt-010、dev-pos-012、dev-pos-013 |
| per-document filter miss | 5 | dev-pos-003、dev-pos-008、dev-pos-010、dev-pt-007、dev-pt-008 |
| adjacent filter miss | 2 | dev-pos-001、dev-pos-004 |
| ranking cutoff miss | 0 | — |
| evidence gate rejection after relevant hit | 0 | — |
| retrieval success | 12 | 见 JSON 明细 |

## Gate 的独立问题

35 个困难负样本仅正确拒绝 7 个，误接受 28 个；总体拒答率 20%。按原因的拒答率为：

| 原因 | 拒答率 |
| --- | ---: |
| false premise | 12.50% |
| missing in-domain value | 14.29% |
| unsupported in-domain conclusion | 20.00% |
| unreleased version | 20.00% |
| out of scope | 20.00% |
| out-of-range implementation | 40.00% |

这与正样本检索漏召回是两条独立问题链：负样本没有 relevant source，不能用 Recall 指标解释；正样本进入 Top-6 后也没有发生 Gate rejection。后续不得把两者合并成一个参数优化。

## 下一轮优先级

1. **检索线优先 candidate recall。** 6/25 个正样本在候选池阶段已经不可恢复，Top-K、过滤和 Gate 都无法补救。下一步只在 Development 比较中文查询归一化、关键词保留和轻量多路查询的单能力增益。
2. **随后单独验证 heading-aware adjacent filtering。** 相邻块规则接触了3个带相关证据的样本，并造成2个终态漏召回；这是范围小但因果清晰的过滤候选。
3. **暂不继续扫每文档配额。** Development 中配额仍造成5个损失，但 quota=4 已完成独立候选周期并失败；重复扫阈值不会解决 candidate miss 或 Gate。
4. **暂不优化 Top-K 排名截断。** 当前没有“通过过滤但落在 Top-6 外”的终态样本，缺少提高 Top-K 或增加 rerank 复杂度的证据。
5. **Gate 维持独立实验线。** 28个 false acceptance 是总体正确性的最大问题，应继续 claim-level deterministic/semantic/combined 消融，但不得与检索候选绑定发布。

因此，下一个最小实现增量是 **eval-only 查询侧 candidate-recall 单能力消融**，不是修改生产默认，也不是再次调整 quota。

## 可复现信息

- 运行提交：`f65ee4a960e1d025f59c07f33424577bf45b30a9`
- Development SHA-256：`50c3d73b7bb67a1f5069d52a9c3d21bb1c8a3481d7ecb4250d7accb7a159d705`
- 原始报告 SHA-256：`b1e7108f9cfc8a6a0efe548f2f092a2921ffd333a89c4646306f7493a587ee9a`
- 完整漏斗：`retrieval_loss_funnel.json`
- 原始逐题报告：`source/retrieval_eval.json`

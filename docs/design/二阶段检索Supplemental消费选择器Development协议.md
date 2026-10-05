# Supplemental 消费选择器非盲 Development 协议

候选 `rank-capped-3-v1` 保持 heading-shadow 原始顺序，只向预算器暴露前三个 supplemental chunk。选择器不读取标签、case ID、Evidence Gate 或答案内容，不改变 Primary Top-6、召回算法、RRF 和候选来源。

正例使用既有 12 条 expansion Development，负例使用 6 条新的 heading 相似困难负例。固定对照为 `fixed@7`，候选为 `rank-capped@3`。正式相关性仍只依据人工 location labels。

机器门槛固定在 `RETRIEVAL_EXPANSION_SELECTOR_DEVELOPMENT_THRESHOLDS.json`：保持 Combined Recall 1.0 和 primary-miss 恢复率 1.0；消费精度至少 0.30；总体及负例平均消费不超过 3；相对 fixed@7 的总体及负例消费下降至少 50%；Primary 保序与预算合规率 100%。

这是非盲 Development 调试，不授权 validation、holdout、Gate/生成、API 或生产接入。

# ADR-001：Claim 语义去重保持 Eval-Only

## 状态

已接受，2026-09-29。

## 背景

项目尝试通过 DraftClaim、确定性类型特征和多语言 NLI 判断回答声明是否被证据支持，以及
声明之间是否语义重复。Development 上的固定候选达到100% precision/recall，但独立
holdout 只有66.67% recall 和80% F1。

## 决策

1. 生产默认 Evidence Gate 保持不变；
2. Claim extraction、NLI 和 semantic duplicate 仅保留为离线评测工具；
3. 禁止根据当前候选自动删除、合并或拒绝生产回答中的 claim；
4. 已运行的 duplicate holdout 不再用于调试或复验；
5. 暂停该研究线，把工程优先级转回核心检索链路。

## 备选方案

- 直接上线 Development 满分候选：被独立 holdout 否决；
- 继续针对 holdout 漏判增加 marker：会污染 holdout，并扩大不可维护规则表；
- 调整 NLI 阈值：失败集中在语言结构和实体边界，没有阈值证据支持；
- 作为 shadow diagnostic 上线：预声明协议要求 holdout 通过，当前不满足。

## 影响

积极影响：生产风险不变，实验资产和失败证据得到保留，项目决策可审计。负面影响：当前
不会获得自动 claim 去重能力。若未来重启，必须建立新的 Development 周期和新的 holdout。


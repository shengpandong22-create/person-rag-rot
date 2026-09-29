# Evidence Gate / Claim Evaluation 实验结论

## 1. 结论摘要

本轮工作完成了从检索诊断、claim-level Gate、NLI、LLM DraftClaim 抽取、稳定性测试到
独立 holdout 的完整闭环。最终结论不是“优化成功上线”，而是：

- 检索阶段已经能把失败定位到 candidate recall 和每文档过滤；
- LLM 可以稳定输出严格 DraftClaim JSON，但 claim 边界仍存在表达波动；
- 类型化特征显著提升 Development duplicate F1；
- 独立 holdout 证明 duplicate 候选召回不足，候选被拒绝；
- 生产 Evidence Gate 和自动 claim 删除均保持不变。

## 2. 关键实验结果

### 2.1 Validation 检索消融

| 模式 | Recall@1 | Recall@3 | Recall@6 | MRR | P95 延迟 |
|---|---:|---:|---:|---:|---:|
| vector-only | 35.29% | 52.94% | 70.59% | 48.53% | 58.55 ms |
| text-only | 17.65% | 35.29% | 41.18% | 26.67% | 50.14 ms |
| RRF | 29.41% | 52.94% | 70.59% | 44.61% | 355.76 ms |
| RRF + heuristic | 17.65% | 52.94% | 70.59% | 36.47% | 95.79 ms |

Vector-only 在当前知识库和冻结 Validation 上是最强基线。阶段诊断进一步显示：

- Candidate Recall@20：88.24%；
- Pre-filter Recall@6：82.35%；
- Post-filter Recall@6：70.59%；
- 5个正样本 Top-6 漏召回中，2个未进入候选池，3个被每文档配额过滤。

### 2.2 DraftClaim 与 NLI

- 人工 DraftClaim fixture：NLI accuracy 86.67%；
- 初始5题 LLM extractor：schema 100%，必要声明召回100%；
- 扩展15题三轮：必要声明召回81.82%～84.85%，claim 集稳定率73.33%；
- Boundary v2：必要声明召回96.97%，claim 集稳定率93.33%～100%；
- 主语签名解析率：79.07%。

扩展数据证明，小样本满分不能代表泛化；结构化输出稳定和语义边界稳定是两个不同问题。

### 2.3 Duplicate Development

22组平衡 duplicate-pair Development 上：

| 策略 | Precision | Recall | F1 |
|---|---:|---:|---:|
| NLI baseline | 77.78% | 63.64% | 70.00% |
| 五类 typed features | 84.62% | 100.00% | 91.67% |
| Typed features + entity veto | 100.00% | 100.00% | 100.00% |

Alias、pronoun、number、date 各自修复一个不同漏判；negation 在该 Development 集上没有
增益。Entity veto 修复两个不同主体导致的 false positive。

### 2.4 独立 Holdout

新建24组、正负各12组且与 Development 文本无重叠的 holdout，预先声明：precision ≥95%、
recall ≥90%、F1 ≥92%、entity 类 FP=0。固定候选只运行一次：

| Precision | Recall | F1 | Entity FP | 结论 |
|---:|---:|---:|---:|---|
| 100.00% | 66.67% | 80.00% | 0 | **不通过** |

4个漏判来自别名谓词改写、两类代词解析和 entity 边界误切。该 holdout 已消耗，不得用于
修改候选后重跑。

## 3. 决策链

1. 小样本成功只证明链路可运行，因此扩充并冻结 Development；
2. 三轮波动暴露 claim boundary 问题，因此先规范边界而非调 NLI 阈值；
3. NLI 忽略主体，因此增加 typed subject/entity 诊断；
4. Development 达到100%后仍不发布，而是建设独立 holdout；
5. Holdout recall 失败，因此拒绝候选，不进入 shadow 或生产。

## 4. 面试价值

这一实验体现的不是“堆模型”，而是评测工程能力：严格数据隔离、指标定义、失败归因、
单能力消融、冻结候选、一次性 holdout 和基于证据拒绝上线。项目因此从“有 Evidence Gate”
升级为“能证明 Gate 在什么边界内可靠，也能在证据不足时停止发布”。

## 5. 下一步

Claim duplicate 研究暂时关闭。核心 RAG 的下一项优先级是每文档配额消融，因为 Validation
中3/5正样本漏召回发生在该过滤阶段，直接影响用户能否得到完整答案。


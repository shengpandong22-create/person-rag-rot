# Frozen Trigger Development Baseline

## 固定配置

- dataset：`retrieval_trigger_development_v1.jsonl`
- dataset SHA-256：`588d1b23c1932df51157f1f786a96c5e70b6cc3769c75be2f463235fe136b0bc`
- experiment：`vector-only`
- candidate expansion：`heading-shadow`
- supplemental consumption：`none`
- top_k / candidate_k：`6 / 20`
- RRF、heuristic、Evidence Gate、生产默认值：未修改

本次运行只刻画冻结 fixture，不据此改数据。宿主机损坏的 SciPy wheel 已按锁定版本
重新安装；embedding provider/model 与知识库保持 `bge / BAAI/bge-small-zh-v1.5`。

## 总体结果

| 指标 | 结果 |
| --- | ---: |
| 正例数 | 12 |
| 主 Recall@1 | 0.0833 |
| 主 Recall@3 | 0.0833 |
| 主 Recall@6 | 0.1667 |
| Candidate Recall@20 | 0.5833 |
| 主@6 + supplemental@1 | 0.3333 |
| 主@6 + supplemental@20 | 0.4167 |
| MRR | 0.1042 |
| Negative rejection | 0.0000 |

P95 包含首次加载 BGE 模型的冷启动（16.5 秒），不能当作稳态线上延迟结论。

## 四类行为确认

| 场景 | 主 Top-6 命中 | supplemental@1 | supplemental@20 | Gate 拒绝 |
| --- | ---: | ---: | ---: | ---: |
| heading 相似困难负例 | 0/4 | 0/4 | 0/4 | 0/4 |
| 低词面语义正例 | 0/4 | 0/4 | 1/4 | 4/4 |
| 高置信漏召回风险 | 0/4 | 1/4 | 1/4 | 1/4 |
| heading/vector 分歧不触发边界 | 2/4 | 1/4 | 1/4 | 1/4 |

关键发现：

1. 四条 heading 相似负例全部被当前 Gate 接受，说明“标题很像”不仅不能作为触发
   充分条件，也暴露了独立的 false-acceptance 问题。
2. 四条低词面语义正例全部被主 Top-6 漏掉，heading lexical 只能在一条的 rank 18
   找回。heading 补充路不能解决一般语义改写召回。
3. 高置信风险组四条全部主 Top-6 漏证据，但只有 `trg-hc-004` 被 supplemental rank 1
   找回；该样本 vector top-1 为 0.6871，且主 Gate 错误接受，符合实际可补救的
   high-confidence miss。
4. 预期“不触发”的 `trg-dn-003` 实际主 Top-6 漏掉复合问题证据，同时 supplemental
   rank 1 命中。冻结后的行为刻画与人工场景意图发生冲突，必须保留并显式报告，不能
   回改 v1 来美化指标。

人工 expected trigger 有 8 条，但按“主 Top-6 漏证据且 supplemental rank 1 命中”
定义的实际可补救样本只有 2 条：两者仅一条重合；另有一条来自 expected no-trigger。

## 预先声明规则外部检验

规则及阈值来自此前 60 条 Development 分析，本次没有重新扫描阈值：

| 规则 | 触发数 | 对 expected trigger F1 | 对实际可补救 F1 |
| --- | ---: | ---: | ---: |
| overlap >= 0.416667 | 0 | 0 | 0 |
| heading score >= 10 | 1 | 0 | 0 |
| overlap >= 0.363636 AND score >= 10 | 0 | 0 | 0 |
| overlap >= 0.416667 OR score >= 22 | 0 | 0 | 0 |

唯一被 `heading score >= 10` 触发的是困难负例 `trg-hn-003`。四条规则对人工意图和
实际可补救性的召回均为 0，因此全部拒绝，不进入 regression 或 validation。

## 决策

- 冻结 fixture 有效地揭示了旧 Development 上看似较强的词面/heading 分数规则不能
  外推；不再继续扫描这两个阈值。
- heading-shadow 仍只保留诊断价值，不能升级为消费候选。
- 下一检索工作应回到低词面语义 candidate recall，而不是继续设计 heading 触发器。
- Evidence Gate 的四个 heading 相似负例 false acceptance 应进入独立 Gate 诊断线，
  不与召回算法改动混在一起。

机器可读产物：

- `trigger_development_baseline/retrieval_eval.json`
- `trigger_development_baseline/trigger_analysis.json`

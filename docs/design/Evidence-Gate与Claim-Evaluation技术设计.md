# Evidence Gate 与 Claim Evaluation 技术设计

## 1. 目标与边界

Evidence Gate 的职责不是证明大模型永远正确，而是在回答生成前后建立可测量的可信边界：

1. 检索阶段判断是否存在足以支撑回答的候选证据；
2. 回答阶段限制引用只能来自本轮检索上下文；
3. 证据不足时拒答或显式降级；
4. 离线评测区分检索失败、排序失败、过滤失败和证据判断失败。

生产默认仍使用现有确定性 Evidence Gate。本文描述的 clause、NLI、DraftClaim、LLM claim
extractor 和 semantic duplicate 能力均为 eval-only，未接入生产组装。

## 2. 分层结构

```text
Question
  -> Retriever candidates
  -> diversity filters / Top-K
  -> deterministic Evidence Gate
  -> answer generation
  -> citation whitelist

Eval-only branch:
Question + draft answer + evidence
  -> strict DraftClaim JSON extraction
  -> claim boundary normalization
  -> deterministic typed checks
  -> NLI entailment / neutral / contradiction
  -> typed duplicate diagnostics
  -> offline metrics and failure attribution
```

### 2.1 检索证据契约

正式 Recall/MRR 只依据人工 `relevant_sources` 解析到的 chunk。Diagnostic keywords 只能帮助
定位问题，不能替代正式相关性标签。证据使用稳定的 `document_logical_name + heading_path`
定位，避免数据库 chunk UUID 重建后标签失效。

### 2.2 DraftClaim 契约

每条声明至少包含：

- `claim_id`：单次抽取内唯一标识；
- `text`：可验证陈述；
- `required`：是否直接回答用户需求；
- `origin`：当前 LLM 抽取固定为 `model_draft`。

LLM 输出由 Pydantic 严格校验，禁止未知字段。Schema 合法不代表语义正确；抽取后仍需
测量必要声明召回、多余声明、无证据声明和 NLI 保留比例。

### 2.3 确定性与语义判断

确定性层负责可解释且高置信的结构：数值、日期、否定、版本、实体身份和部分代词关系。
NLI 层判断 evidence 是否蕴含、未知或矛盾。组合策略遵循保守原则：明确冲突可以否决，
未解析不能伪装成确认。

### 2.4 Typed duplicate 诊断

重复判断被拆成独立特征：

- alias normalization；
- pronoun resolution；
- negation normalization；
- number normalization；
- date normalization；
- entity identity veto。

这些能力只用于离线诊断。自动删除声明属于不可逆行为，必须同时满足独立 holdout 和线上
shadow 证据；当前候选未通过 holdout，因此禁止生产接入。

## 3. 数据隔离与复现

- Development：建设能力、单能力消融和失败分析；
- Regression：保护已有行为；
- Validation：参数与固定候选选择；
- Holdout：候选固定后只运行一次，不参与调参。

每份报告记录数据集 hash、冻结清单 hash、Git commit、模型、运行参数、耗时和逐题结果。
Holdout 失败后不得根据其题目修改候选并在同一 holdout 上重跑。

## 4. 生产安全边界

当前明确不做：

- 不切换生产 Evidence Gate；
- 不根据 semantic duplicate 自动删除 claim；
- 不让 NLI 结果直接覆盖回答；
- 不把 Development 满分描述成生产能力；
- 不重复运行已经消耗的 holdout。

这一边界使项目能够展示语义评测研究，同时保持默认 RAG 行为和线上风险不变。


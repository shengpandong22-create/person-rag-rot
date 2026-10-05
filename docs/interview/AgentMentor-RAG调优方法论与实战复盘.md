# AgentMentor RAG 调优方法论与实战复盘

> 适用场景：项目复盘、后续继续调优、技术方案评审、简历与面试讲解。  
> 核心结论：这轮工作的价值不只是把某个指标调高，而是建立了一套能定位损失、隔离变量、拒绝坏候选并保护生产链路的可信调优体系。

## 1. 一页结论

这轮优化解决了三个更根本的问题：

1. **以前不知道错在哪里。** 一条回答失败，可能是标签不可解析、候选没召回、排序截断、过滤误删、Evidence Gate 拒绝或生成阶段越界。现在可以沿损失漏斗逐层归因。
2. **以前容易把局部提升误认为整体提升。** Development 上的 100% 不等于能进生产；候选还必须经过 regression、validation 和独立 acceptance，并满足预先提交的硬门槛。
3. **以前缺少“停止优化”的证据。** V3 Gate 和二阶段检索都产生过局部收益，但独立验收或消费精度证明它们不具备生产资格。系统保留失败结论，而不是为了上线继续调阈值。

最终沉淀出的工程能力包括：

- 可冻结、可追溯的数据集与实验身份；
- vector-only、text-only、RRF、RRF + heuristic 的单变量消融；
- candidate → ranking → filter → gate 的检索损失漏斗；
- claim、relation、value、unit、provenance、span 的类型化诊断；
- 单调安全的 supplemental 检索与上下文预算；
- 协议先行、一次性验收、feature flag 和回退边界；
- 对“安全但无效”候选做出明确的不上线决策。

一句话概括：**把“凭感觉改 RAG”升级成“用冻结数据、损失漏斗和硬门槛管理候选”。**

## 2. 为什么必须优化

### 2.1 单看最终答案，无法定位根因

RAG 的最终正确率是多个环节相乘的结果，可以抽象为：

```text
最终可信回答
  = 标签可解析
  × 候选证据被召回
  × 证据进入最终上下文
  × Evidence Gate 正确判断
  × 生成器忠于证据
  × 引用可追溯
```

任何一项接近 0，最终答案都会失败。若只看“答对/答错”，常见误判包括：

- 候选池根本没有证据，却去调 rerank 权重；
- 证据已召回但被配额过滤，却去改 embedding；
- 检索正确但 Gate 拒绝，却把问题归咎于召回；
- 负例拒答正常，却为了提高正例召回而放松阈值；
- Development 提升明显，就直接认为可以上线。

因此第一原则不是“先改算法”，而是**先让每一层损失可观测**。

### 2.2 传统相关性指标不足以约束可信回答

Recall@K 和 MRR 只能说明相关证据是否被检索以及排位如何，不能回答：

- 问题要求的精确数值和单位是否真的存在；
- “阈值”是否被误当成“准确率保证”；
- 表格中的值是否绑定到了正确的行和列；
- 多子句问题是否只回答了一半；
- 错误前提是否被系统顺着回答；
- 新增上下文是否只是重复、噪声或诱导性证据。

因此评测必须同时覆盖三类目标：

| 层级 | 关注问题 | 代表指标 |
| --- | --- | --- |
| 检索 | 证据有没有、排得够不够前 | candidate recall、Recall@K、MRR |
| 证据判断 | 证据是否足以支撑需求 | full/partial/none、negative rejection、binding accuracy |
| 系统成本 | 提升是否值得 | P50/P95 延迟、候选数、上下文字符数、消费精度 |

### 2.3 没有数据隔离，指标会被“调出来”

同一批样本既用于发现问题、修改实现，又用于证明效果，结论必然乐观。因此本项目将数据角色拆开：

| 数据层 | 用途 | 是否允许看失败样本调参 |
| --- | --- | --- |
| Development | 诊断、构造特征、单能力消融 | 允许 |
| Regression | 防止已有能力退化 | 不用于追求新收益 |
| Validation | 候选选择与跨集稳定性 | 按已声明协议运行 |
| Acceptance/Holdout | 独立最终验收 | 冻结后不得据此调参 |

正式相关性只使用人工 `relevant_sources` 解析出的 chunk；`diagnostic_keywords` 只用于解释，不得替代标签。数据集、freeze manifest、知识库和实现文件均记录 SHA-256，防止“代码没变、实验身份却悄悄变了”。

## 3. 这轮是如何优化的

### 3.1 先重建评测地基

首先完成的不是新算法，而是评测体系 v2：

- `full / partial / none` 三档 answerability；
- `label_origin` 与人工标签来源；
- 稳定的 `document_logical_name + heading_path` 证据定位；
- split 重叠检查、标签可解析检查和冻结机制；
- 数据集 hash、知识库 fingerprint、文档 hash、模型与运行参数；
- 每条样本的检索 trace、证据决策和统一失败类别。

这一步的意义是：后续任何“提升”都能回答**使用了什么数据、运行了什么实现、改变了哪个变量、为什么判定通过**。

### 3.2 用消融确定现有组件的真实贡献

在相同 validation 上比较四种模式：

| 模式 | Recall@1 | Recall@3 | Recall@6 | MRR | P95 延迟 |
| --- | ---: | ---: | ---: | ---: | ---: |
| vector-only | 35.29% | 52.94% | 70.59% | 48.53% | 58.55 ms |
| text-only | 17.65% | 35.29% | 41.18% | 26.67% | 50.14 ms |
| RRF | 29.41% | 52.94% | 70.59% | 44.61% | 355.76 ms |
| RRF + heuristic | 17.65% | 52.94% | 70.59% | 36.47% | 95.79 ms |

该结果揭示了两个重要事实：

1. 复杂组合并未自动优于 vector-only，不能把“组件更多”当成“效果更好”。
2. RRF + heuristic 的 Recall@6 没下降，但头部排序变差；如果只看 Recall@6，会漏掉质量退化。

因此后续没有针对单个失败样本调整 RRF 权重，而是进入检索损失漏斗。

### 3.3 用漏斗把召回、排序和过滤分开

漏斗诊断结果：

| 阶段 | 指标 |
| --- | ---: |
| candidate recall@20 | 88.24% |
| pre-filter recall@6 | 82.35% |
| post-filter recall@6 | 70.59% |

5 个 Top-6 miss 中：

- 2 个证据不在 candidate pool，属于 candidate recall 问题；
- 3 个证据曾被召回，但被每文档配额等后过滤丢失。

这直接改变了优化方向：

- candidate miss 应研究查询视图或独立候选路；
- filter miss 应审计配额、相邻块去重和 heading 边界；
- 两者不能混为一个“检索差”的问题。

每文档配额从 3 调到 4 时，validation Recall@6 从 70.59% 提升到 82.35%，与 unlimited 一致。但这只能证明后过滤损失被缓解，不能证明所有 candidate recall 问题已经解决。

### 3.4 将 Evidence Gate 从模糊分数拆成类型化判断

Gate 实验依次经历：

1. coverage 阈值候选；
2. clause-aware / demand-aware 诊断；
3. deterministic、semantic NLI、combined 对比；
4. `DraftClaim` 契约和 claim normalization；
5. alias、pronoun、negation、number、date 单能力消融；
6. relation → value/unit → provenance/span 的类型化 binding。

阶段性收益包括：

- 人工 fixture 上 NLI accuracy 86.67%；
- claim boundary v2 的必要声明召回率 96.97%；
- claim-set stability 提升到 93.33%～100%；
- 语义重复专项中，typed + entity veto 达到 precision/recall/F1 100%/100%/100%。

但独立 holdout 上 typed 去重 recall 只有 66.67%，没有达到门槛。这说明专项集上的满分不能外推为泛化能力。

Relation-Value V3 的独立 acceptance 更关键：

| 指标 | 实际 | 门槛 |
| --- | ---: | ---: |
| demand accuracy | 32.56% | 90% |
| positive demand recall | 6.45% | 87.10% |
| positive all-demands row accuracy | 8.33% | 83.33% |
| negative rejection | 100% | 100% |
| binding precision | 22.22% | 90% |
| paired discrimination | 9.09% | 90.91% |

V3 的结论不是“代码有 bug”，而是**安全但基本不工作**：负例拒绝很好、速度也够快，但正例 binding recall 和关系区分能力远不具备生产价值。因此实验线被正式关闭，没有降低门槛，也没有在 acceptance 上继续调参。

### 3.5 二阶段检索：先保证单调安全，再验证是否值得消费

二阶段检索采用了“primary 不动、supplemental 只追加”的设计：

- 原 Top-6 的 ID 和顺序必须保持；
- supplemental 与真实 `final_results` 去重，而不是与全部 vector candidates 去重；
- 预算器支持 7/13 个 chunk 与 7000/18000 字符预算；
- feature flag 默认关闭；
- 不调用 Gate、生成器，不接 API 和前端；
- repository、trace 和 orchestration 先以骨架方式落地。

修复 `primary-context-dedupe-v1` 后，非盲 Development 的 combined recall 从 0.50 提升到 1.00，6/6 个 miss 被补回。随后 regression 验证得到：

- 30/30 样本原 Top-6 完全一致；
- primary recall 保持 0.55；
- combined recall 提升到 0.70；
- P95 增量约 100 ms；
- Gate 和生成调用次数均为 0。

但是另一个指标暴露了生产风险：固定消费 supplemental 的 regression precision 仅 0.019，10 个负例生成了 185 个 supplemental candidates。即使 `rank_cap=3` 在 Development 保住 1.00 recall 并减少约 57% 消费，precision 也只有 0.2353，低于 0.30 门槛。

随后诊断 heading 路径增量、关系词匹配、章节分歧和重复概念等触发特征，仍无法稳定区分补回正例与困难负例。因此最终选择：

- 保留 candidate provider、预算器、repository 和单调安全基础设施；
- 保持 feature flag 关闭；
- 不接 Gate、生成、API 和前端；
- 将“缺少可靠消费触发信号”记录为已知限制。

这是一个非常重要的结论：**combined recall 提升不等于用户体验提升；如果上下文消费精度极低，新增候选可能只是把风险和成本推给生成器。**

## 4. 可复用的 RAG 调优方法

### 4.1 先写假设，再写代码

每个实验只回答一个问题：

```text
现象：哪些样本、哪个指标失败？
假设：损失发生在哪一层？
唯一变量：本次只改变什么？
不变量：哪些排序、阈值、模型和数据禁止变化？
收益指标：希望改善什么？
安全指标：哪些指标绝不能下降？
成本上限：延迟、候选数、上下文长度最多增加多少？
退出条件：什么结果意味着停止该方向？
```

如果无法用一句话说明唯一变量，就不应开始实验。

### 4.2 建立统一损失漏斗

建议每条样本至少记录以下阶段：

```text
label resolution
  → candidate pool
  → fused/reranked list
  → post-filter list
  → final context
  → evidence decision
  → answer/citation
```

归因决策：

| 观测 | 应优先处理 |
| --- | --- |
| 标签路径无法映射 chunk | 数据和索引一致性 |
| Top-N candidate 中没有证据 | query/candidate recall |
| candidate 有，Top-K 没有 | ranking/fusion |
| pre-filter 有，post-filter 没有 | quota/dedupe/filter |
| final context 有，Gate 拒绝 | evidence decision |
| 负例被接受 | demand binding / false premise |
| Gate 正确，答案仍越界 | generation/citation |
| recall 提升但消费精度低 | selector/trigger/context budget |

不要跨层开药：candidate miss 不能靠放松 Gate 修复，filter miss 也不应先换 embedding。

### 4.3 单变量消融，而不是堆功能

推荐顺序：

1. baseline；
2. 只增加一个能力；
3. 保持数据、Top-K 和其余参数一致；
4. 输出总体指标和逐样本差异；
5. 标记提升、退化和未变化；
6. 解释机制，而不只报告数字。

例如检索消融必须能分清 vector、text、RRF、heuristic 各自贡献；Gate 消融必须能分清 deterministic、semantic 和 combined 的贡献。多个变量同时变化，即使指标提升，也无法形成可复用结论。

### 4.4 协议和门槛必须先于正式运行

正式验证前先提交：

- 候选实现身份及 SHA-256；
- 数据集、freeze manifest 和知识库 fingerprint；
- 完整运行命令和固定参数；
- 收益门槛、安全门槛、成本上限；
- 是否允许重跑以及基础设施失败的处理规则；
- 失败后的分流规则。

这样可以避免看到结果后临时降低门槛或修改指标口径。算法失败和执行失败必须分开：数据库断连可以按协议恢复执行；候选指标失败不能借“再跑一次”继续调参。

### 4.5 正确使用四层数据

```text
Development：发现规律、允许失败、允许迭代
      ↓ 候选固定
Regression：证明没有破坏已有能力
      ↓ 协议固定
Validation：证明跨集稳定，不针对失败样本回调
      ↓ 新建并冻结
Acceptance：独立标注、盲审、一次性最终裁决
```

如果 acceptance 被用于调参，它就已经变成 Development；下一次正式验收必须重新建设独立数据集。

### 4.6 同时管理收益、安全和成本

候选资格不应只有一个数字：

| 维度 | 示例硬门槛 |
| --- | --- |
| 收益 | Recall@6、positive demand recall、联合证据召回 |
| 安全 | 原 Top-6 完全一致、negative rejection 不下降 |
| 精度 | supplemental consumption precision、binding precision |
| 成本 | P95 延迟、平均候选数、上下文字符数 |
| 稳定 | 多轮输出一致率、schema 合法率 |
| 可运维 | feature flag、trace、回退路径、默认关闭 |

一个候选可能“更安全但没效果”，也可能“召回更高但噪声巨大”。两者都不应直接上线。

## 5. 最容易踩的坑

### 5.1 用关键词命中代替人工相关性

关键词适合诊断，不适合正式 Recall/MRR。词面命中可能对应错误章节、错误关系或错误值。

### 5.2 针对单个 case 调权重

为修复一个样本调整 RRF、rerank 或阈值，很可能只是把该样本排上来，同时破坏其他样本。应先确认它属于候选、排序还是过滤问题。

### 5.3 多个变化叠在一起

查询改写、配额、rerank、Gate 同时变化，即使提升也无法知道贡献来源，更无法安全回滚。

### 5.4 在 holdout/acceptance 上反复试

一旦读了失败样本并据此改实现，该数据就不再独立。正确做法是关闭候选、回到非盲 Development，下一候选使用新的独立验收集。

### 5.5 只看 recall，不看上下文消费精度

二阶段检索就是典型案例：证据补回成功，但大量无效候选也被加入。若不测消费精度、字符预算和负例开销，会把风险隐藏到生成阶段。

### 5.6 把“默认关闭”当成已经上线

eval-only 实现、feature flag 默认关闭、未注册路由，都表示它仍是实验基础设施。文档中必须明确“已实现”“已验证”“已授权生产”是三个不同状态。

## 6. 可直接复制的实验模板

### 6.1 实验卡

```markdown
# <候选名> 实验卡

- 问题：
- 证据：
- 假设：
- 唯一变量：
- 保持不变：
- Development 数据：
- 收益指标与门槛：
- 安全指标与门槛：
- 成本上限：
- 实现 commit / SHA-256：
- 数据集 / freeze SHA-256：
- 固定命令：
- 通过后的下一步：
- 失败后的处理：关闭候选 / 返回 Development，不在正式集调参。
```

### 6.2 每条样本的最小 trace

```json
{
  "case_id": "...",
  "experiment_mode": "...",
  "retrieved_chunk_ids": [],
  "document_logical_name": "...",
  "heading_path": [],
  "vector_rank": null,
  "vector_score": null,
  "text_rank": null,
  "text_score": null,
  "rrf_score": null,
  "rerank_score": null,
  "candidate_hit": false,
  "prefilter_hit": false,
  "postfilter_hit": false,
  "evidence_decision": "...",
  "failure_category": "...",
  "latency_ms": 0,
  "consumed_chunk_count": 0,
  "consumed_char_count": 0
}
```

统一失败类别建议保留：`source_label_unresolved`、`retrieval_miss`、`ranking_miss`、`evidence_gate_rejection`、`correct_rejection`、`false_acceptance`、`partial_answer_boundary`；如果需要更细粒度，可新增 `candidate_miss`、`post_filter_miss`，但不要覆盖原始观测。

### 6.3 候选上线检查表

- [ ] 数据标签可解析，split 无重叠；
- [ ] 实现、协议、数据和门槛已冻结；
- [ ] 单变量贡献可解释；
- [ ] regression 无退化；
- [ ] validation 跨集稳定；
- [ ] 独立 acceptance 达到所有硬门槛；
- [ ] 延迟、候选数和上下文预算可接受；
- [ ] 负例和错误前提没有新增误接受；
- [ ] feature flag 默认关闭并可快速回退；
- [ ] trace、监控和审计字段完整；
- [ ] 生产接入经过单独授权。

只要一项硬门槛失败，就不应用其他指标的超额收益抵消。

## 7. 本轮哪些真正完成，哪些没有上线

### 已完成并可复用

- 评测 v2、人工标签、冻结和 hash；
- 四组检索消融与逐样本 trace；
- 检索损失漏斗和失败归因；
- claim/evidence、relation/value 的 eval-only 框架；
- 独立盲审、冲突裁决和 acceptance runner；
- 二阶段检索 contract、repository、预算器、编排骨架；
- primary-context 去重修复及 regression 安全验证；
- V3 与二阶段检索的正式关闭决策。

### 明确没有做的生产变更

- 没有切换生产 Evidence Gate；
- 没有启用 Relation-Value V3；
- 没有默认开启二阶段检索；
- 没有把 supplemental 接入生成链路；
- 没有注册用户可见 API 或前端按钮；
- 没有为了通过验收降低门槛或针对 holdout 调参。

因此这轮最准确的成果描述是：**评测与实验治理已经显著增强，若干候选得到可信验证；生产算法保持保守，未把未达标候选带入用户链路。**

## 8. 面试中怎么讲

### 30 秒版本

> 我没有直接堆 reranker 或调 RRF，而是先重建 RAG 评测体系，把失败拆成 candidate recall、排序、过滤、Evidence Gate 和生成五层。消融发现 validation 的 candidate recall@20 是 88.24%，但 post-filter Recall@6 只有 70.59%，说明主要损失不全在 embedding。我们修复了配额和 supplemental 去重边界，二阶段检索在 Development 补回 6/6 缺失证据，并保证 regression 30/30 原 Top-6 不变；但独立诊断发现 supplemental 消费精度仅 1.9%，所以没有接生产。这个项目的核心价值是建立了可复现、可拒绝坏候选的评测闭环。

### 两分钟版本的结构

1. **背景：** RAG 回答失败无法定位，原有指标混合了召回、过滤和 Gate。
2. **任务：** 建立能安全评估候选、保护已有能力的调优体系。
3. **行动：** 重建数据标签与冻结；做四组消融；构造损失漏斗；对 Gate 和二阶段检索做类型化、单变量实验；为正式验证预提交协议和硬门槛。
4. **结果：** 定位 5 个 Top-6 miss 中 2 个来自 candidate、3 个来自过滤；修复去重边界后补回 6/6 证据且原 Top-6 完全不变；同时用独立验收挡住了 positive recall 仅 6.45% 的 V3 和消费精度仅 1.9% 的二阶段生产接入。
5. **反思：** 指标提升不等于可上线，独立数据、成本指标和停止规则与算法本身同样重要。

这个表述的亮点不是“我调出了一个漂亮数字”，而是“我能解释系统为什么失败、怎样证明修复有效、怎样阻止局部最优污染生产”。

## 9. 下一次继续调优时的建议

当前不建议继续围绕同一批 Development 样本调整 heading trigger 或 fixed quota。若重启检索优化，应：

1. 新建未被现有规则消费的非盲 Development；
2. 优先研究低词面语义 candidate recall，而非继续调 RRF 权重；
3. 将“是否召回候选”和“是否消费上下文”拆为两个模型或规则；
4. 新候选必须同时改善证据召回和消费精度；
5. Gate 继续作为独立实验线，不用它掩盖 retrieval miss；
6. 候选固定后再声明新的 validation/acceptance 协议。

## 10. 关联材料

- [Evidence Gate 与 Claim Evaluation 技术设计](../design/Evidence-Gate与Claim-Evaluation技术设计.md)
- [Evidence Gate / Claim Evaluation 实验结论](../evaluations/evidence-gate-claim-evaluation-20260929.md)
- [Relation-Value V3 独立验收](../evaluations/relation-value-v3-acceptance-20261004.md)
- [ADR-002：关闭 Relation-Value V3 实验线](../decisions/ADR-002-关闭RelationValueV3实验线.md)
- [用户触发二阶段检索 API 与预算设计](../design/用户触发二阶段检索API与预算设计.md)
- [二阶段检索 Regression 安全验证协议](../design/二阶段检索Regression安全验证协议.md)
- [ADR-003：阶段性关闭二阶段检索生产接入](../decisions/ADR-003-阶段性关闭二阶段检索生产接入.md)

---

最后的工程原则：**先把失败变得可解释，再把候选变得可比较，最后才讨论是否上线。**

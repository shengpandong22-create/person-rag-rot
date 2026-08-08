# 第 3 课：混合检索与可信 RAG 回答

> 日期：2026-08-05  
> 状态：已学完 ✅

---

## 一、教案正文

### 3.1 先说结论

当前检索不是只有 pgvector，而是：

```
向量召回（余弦相似度）
       ┐
       ├→ RRF 排名融合 → 每文档限额/相邻块去重 → Top K
全文召回（tsvector）
       ┘
```

检索之后还有三道防线：

```
检索结果 → 词汇化证据判断 → 分数阈值门禁 → 证据不足拒答
                                        ↓ 证据够
                                   LLM 生成 → 引用白名单校验
```

---

### 3.2 为什么需要两路检索

| 查询类型   | 示例                             | 适合的检索           |
| ---------- | -------------------------------- | -------------------- |
| 语义改写   | "如何恢复中断的 Agent 流程"      | 向量检索（语义相近） |
| 精确标识符 | `WorkflowCheckpointModel`、`RRF` | 全文检索（精确匹配） |

技术资料同时包含自然语言和精确标识符，单路召回容易漏失。

---

### 3.3 RRF 融合：为什么不能直接加分数

#### 核心问题：两种分数不在同一尺度上

余弦相似度范围 [-1, 1]，全文 `ts_rank_cd` 没有固定上限——一个是归一化的几何距离，一个是自由增长的匹配得分。直接相加会一方权重碾压另一方。

#### RRF 公式

```python
def reciprocal_rank_fusion(ranked_lists, *, rrf_k=60):
    scores = {}
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
    return scores
```

公式：`score = Σ 1/(k + rank)`

#### 具体计算示例

假设搜"RRF 融合"，两路返回：

```
           向量召回排名    全文召回排名
A（RRF段落）  第1名         第3名
B（pgvector） 第2名         未召回（∞）
C（全文检索） 未召回（∞）     第1名
D（混合检索） 第3名         第2名
```

计算：
```
A: 1/(60+1) + 1/(60+3) = 1/61 + 1/63 = 0.0323  ← 两路都有排名，最高
D: 1/(60+3) + 1/(60+2) = 1/63 + 1/62 = 0.0320
C: 1/(60+1)          = 1/61      = 0.0164   ← 只有全文路
B: 1/(60+2)          = 1/62      = 0.0161   ← 只有向量路
```

最终排序：**A > D > C > B**

A 排第一因为两路都召回了——这正是 RRF 的核心价值。

#### RRF 的三条核心价值

| 价值           | 为什么                                            |
| -------------- | ------------------------------------------------- |
| **量纲无关**   | 不管原始分是 0.72 还是 9500，RRF 只看排名         |
| **双路有加成** | 两路都召回 → 两个排名都参与计算 → 天然加分        |
| **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献，不会被粗暴截断 |

#### RRF 解决了什么，没解决什么

| ✅ 解决了                             | ❌ 没解决                                 |
| ------------------------------------ | ---------------------------------------- |
| 两种异构分数不可比的问题             | 如果两路都没召回正确答案，RRF 也救不了   |
| 排名融合的稳定性（不依赖原始分尺度） | 检索质量的上限仍取决于两路各自的召回能力 |

---

### 3.4 检索代码的核心流程

```python
# infrastructure/retriever.py

# 1. 向量召回
vector_candidates = await self._vector_candidates(session, query, normalized)

# 2. 全文召回（仅 HYBRID 模式）
text_candidates = await self._text_candidates(session, query, normalized)

# 3. RRF 融合
vector_ranks = {item.chunk.id: item.rank for item in vector_candidates}
text_ranks = {item.chunk.id: item.rank for item in text_candidates}
fused = reciprocal_rank_fusion([list(vector_ranks), list(text_ranks)])

# 4. 按融合分排序
ordered_ids = sorted(fused, key=lambda chunk_id: fused[chunk_id], reverse=True)
```

#### 向量查询

```python
vector = await self._embedding.embed_query(normalized)
distance = KnowledgeChunkModel.embedding.cosine_distance(vector)
statement = self._base_query(query).order_by(distance).limit(query.candidate_k)
```

#### 全文查询

```python
ts_query = func.websearch_to_tsquery("simple", normalized)
rank_expr = func.ts_rank_cd(KnowledgeChunkModel.search_text, ts_query)
statement = (
    self._base_query(query)
    .where(KnowledgeChunkModel.search_text.op("@@")(ts_query))
    .order_by(rank_expr.desc())
)
```

---

### 3.5 检索后处理：为什么还要限额和去重

#### 每文档限额（max_chunks_per_document）
不加限制：某篇 100 页文档占全部 Top-K → 来源单一。  
加限制后：每篇最多贡献 N 个 chunk → 来源多样化。

#### 相邻块去重
连续相邻 chunk 内容高度重叠 → 去掉后为不同位置腾出空间。

---

### 3.6 第一道防线：词汇化证据判断

```python
def _has_lexical_support(self, question, candidates):
    query_terms = self._evidence_terms(question)      # 从问题提取关键词
    context_terms = set()
    for chunk in candidates[:3]:
        context_terms.update(self._evidence_terms(chunk.content))
        context_terms.update(term.lower() for term in chunk.heading_path)

    overlap = query_terms & context_terms
    # 英文：只要有一词重叠就算通过
    # 中文：至少 2 个 bigram 重叠，且占比 ≥ 18%
```

向量检索可能返回"余弦距离很近但内容不相关"的结果——比如都是"技术文档风格"但讨论完全不同的话题。词汇化判断作为粗筛，确保至少字面上有关联。

---

### 3.7 第二道防线：证据门禁

```python
supported_candidates = self._supported_candidates(question, candidates)
sufficient = (
    bool(supported_candidates)
    and supported_candidates[0].score >= self._min_evidence_score
)

if not sufficient and not allow_model_knowledge:
    return await self._persist(
        answer="当前知识库证据不足，我不能把模型常识伪装成资料结论。",
        citations=[],
        evidence_sufficient=False,
        generation_mode="evidence_guard",
        fallback_reason="insufficient_evidence",
    )
```

核心价值：**不是"模型不知道就不回答"，而是应用层先判断当前资料是否足以支持回答。** 证据不够且用户没允许补充 → 直接拒答。

---

### 3.8 第三道防线：引用白名单

```python
def validate_citations(citation_ids, context):
    allowed = {chunk.chunk_id for chunk in context}
    invalid = [chunk_id for chunk_id in citation_ids if chunk_id not in allowed]
    if invalid:
        raise ValueError("Citations are not in the current retrieval context")
```

#### 引用白名单能做什么
- 防止 LLM 编造不存在或不属于本轮上下文的 Chunk ID
- 保证用户点开引用链接时能看到对应内容

#### 引用白名单不能做什么

| ❌ 不能                           | 为什么                   |
| -------------------------------- | ------------------------ |
| 证明片段完整支持答案中所有 claim | 模型可能断章取义         |
| 证明文档本身一定正确             | 来源合法性 ≠ 内容正确性  |
| 证明检索没有漏掉关键证据         | 没召回的东西白名单管不了 |
| 证明模型没有曲解原文             | 模型可能歪曲 chunk 含义  |

准确表述：**"引用来源合法性校验"**，不是 **"完全消除幻觉"**。

---

### 3.9 LLM 生成层：双路径兜底

```python
async def _generate_answer(self, ...):
    if self._llm is None:
        # 路径 A：确定性组合（无 LLM）
        return (self._compose_grounded_answer(...), "deterministic", "llm_not_configured", ...)
    try:
        # 路径 B：LLM 结构化生成
        output = await self._llm.generate_structured(...)
        ensure_citations_are_valid(output.citation_chunk_ids, candidates)
        if not output.evidence_sufficient and not allow_model_knowledge:
            return ("...证据不足以可靠回答...", "evidence_guard", "llm_rejected_evidence", False)
        return output.answer, "llm", None, evidence_sufficient
    except Exception as error:
        # 路径 C：LLM 失败时降级到确定性路径
        return (self._compose_grounded_answer(...), "deterministic", type(error).__name__, ...)
```

三层降级：无 Key → 有 Key 正常调用 → 调用失败兜底。每次都记录 `generation_mode` + `fallback_reason`。

---

### 3.10 完整 RAG 链路

```
用户提问
    ↓
PostgresHybridRetriever.retrieve
    ├── 向量召回（pgvector cosine_distance）
    ├── 全文召回（tsvector @@ websearch_to_tsquery）
    └── RRF 融合排名
    ↓
每文档限额 + 相邻块去重 → Top K
    ↓
词汇化证据判断（_has_lexical_support）
    ↓
分数阈值门禁（sufficient?）
    ├── 否 + 不允许补充 → 拒答（evidence_guard）
    └── 是 / 允许补充
        ↓
    LLMGateway.generate_structured
        ├── 无 LLM → _compose_grounded_answer（deterministic）
        ├── LLM 成功 → 结构化回答 + 引用校验
        └── LLM 失败 → 降级到 deterministic
    ↓
validate_citations（引用白名单）
    ↓
_persist（写 ChatSession + ChatMessage + ChatCitation）
    ↓
返回 AnswerResult（答案 + 引用 + 诊断信息）
```

---

### 3.11 本课自测

1. 为什么全文分数和向量分数不能直接相加？
2. RRF 解决了什么，又没有解决什么？
3. 引用白名单能做什么、不能做什么？为什么不能说它"完全消除幻觉"？
4. 证据门禁和引用白名单分别在哪一层防护？各自防什么问题？
5. 当前 Embedding 弱的情况下，三道防线分别起了什么作用？

---

## 二、学员疑问与讨论记录

### Q1：RRF 排名融合是怎么计算的，为什么要使用 RRF 融合？

**回答：**

核心问题是余弦相似度 [-1, 1] 和 ts_rank 无上限属于不同量纲，直接相加等于默认"1 单位向量分 = 1 单位全文分"但这个等式不成立。

RRF 不看分数只看排名，公式 `score = Σ 1/(k + rank)`（k=60）。三条核心价值：

| 价值           | 为什么                                   |
| -------------- | ---------------------------------------- |
| **量纲无关**   | 不管原始分是 0.72 还是 9500，只看排名    |
| **双路有加成** | 两路都召回 → 两个排名参与计算 → 天然加分 |
| **长尾不丢弃** | 排名 100 仍有 1/160≈0.0063 的贡献        |

---

### Q2：三道防线在 Embedding 强的时候是否仍然具备存在意义？

**学员核心洞察：**

> 即使 Embedding 强，也存在检索出不准确结果、大模型胡编乱造的情况

**回答：**

**三道防线不是因为 Embedding 弱才存在，Embedding 再强也不能去掉。**

| 防线           | 防的根本问题                       | 强 Embedding 能解决吗？                   |
| -------------- | ---------------------------------- | ----------------------------------------- |
| 词汇化证据判断 | 检索结果和问题字面无关             | ❌ 不能。强 Embedding 也会召回偏题内容     |
| 证据门禁       | 证据不够但把模型常识伪装成资料结论 | ❌ 不能。这是系统契约问题，和检索质量无关  |
| 引用白名单     | LLM 编造 chunk_id                  | ❌ 绝对不能。BGE 管不到 LLM 生成阶段的行为 |

面试金句：
> "三道防线不是弥补 Embedding 弱的过渡方案，而是 RAG 系统的常驻基础设施。弱 Embedding 只是让防线的作用更明显。在一个严肃的 RAG 系统中，这三道防线独立于 Embedding 质量而存在。"

---

## 三、自测结果

全部正确 ✅

| 题号 | 回答                                           | 点评                               |
| ---- | ---------------------------------------------- | ---------------------------------- |
| 1    | 双路得分差距较大导致最准的被过滤               | ✅ 方向对。精确说法：不同量纲不可比 |
| 2    | 解决了/没解决的完整复述                        | ✅ 精确                             |
| 3    | 能做/不能做完整对照，补充了"片段完整支持claim" | ✅ 超出教案范围的理解               |
| 4    | "大模型整理之前"和"大模型回答之后"的时间线     | ✅ 比教案更直观                     |
| 5    | 三道防线作用准确                               | ✅                                  |

---

## 四、本课结论

**自测结果：通过 ✅**

- RRF 原理和计算能讲清，理解量纲不匹配的核心问题
- 三道防线的定位从"补偿弱检索"升级到"独立安全层级"——认知深度超出教案预期
- 引用白名单的边界理解准确，知道"合法性校验 ≠ 消除幻觉"
# 企业 RAG：分块、混合检索与版本治理学习笔记

## 资料来源

- Microsoft Learn, Build Advanced Retrieval-Augmented Generation Systems: https://learn.microsoft.com/en-us/azure/developer/ai/advanced-retrieval-augmented-generation
- Microsoft Learn, RAG and Generative AI in Azure AI Search: https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview

本文为基于官方资料整理的学习笔记，不是原文转载。

## 1. RAG 的核心不是把整篇文档塞给模型

企业文档数量可能远超模型上下文窗口。RAG 的职责是从大量知识中召回少量、相关、可验证的证据，再让模型基于这些证据生成答案。

高质量 RAG 至少包含：

```text
数据摄入 → 解析 → 清洗 → 分块 → 索引
→ Query 处理 → 候选召回 → 排序 → 上下文构造
→ 生成 → 引用与事实校验 → 反馈与评测
```

## 2. 分块策略

固定长度分块实现简单，但可能切断语义结构。结构化分块应利用标题、段落、列表、表格、代码块和页码。

分块需要平衡：

- 块太小：信息不完整，生成阶段缺少上下文；
- 块太大：召回粒度粗，Token 成本增加；
- overlap 太小：跨边界信息丢失；
- overlap 太大：重复候选挤占上下文。

可采用 Small2Big：使用小块做精确召回，再扩展到其父段落或邻近上下文供模型生成。

## 3. 全文检索和向量检索

全文检索适合精确关键词、编号、异常名、API 和产品代号。向量检索适合同义表达和语义改写。

Hybrid Search 将两路召回结合，可以降低单一检索器的盲区。由于两种分数尺度不同，可以使用基于排名的融合，再使用 reranker 对候选进行更精细排序。

## 4. Query 处理

真实用户问题可能包含错别字、缩写、上下文指代和多个意图。可采用：

- Query normalization；
- 术语词典和同义词；
- Query rewrite；
- Query decomposition；
- metadata filter；
- 对话历史压缩。

Query Rewrite 必须保留原问题，并对改写结果进行观测，否则错误改写会让正确知识永远无法召回。

## 5. 索引与文档版本

企业知识持续更新。索引需要保存：

- 文档版本和内容 Hash；
- 来源、责任人和权威等级；
- 生效时间与失效时间；
- 租户和 ACL；
- 解析器、分块和 Embedding 版本；
- Chunk 到原文位置的数据血缘。

更新或撤回文档时，旧向量、全文索引、缓存和派生回答应同步失效。历史报告若引用旧版本，应保留可审计的版本标识，而不是静默指向新内容。

## 6. 检索评测

不能只评价最终答案。应分层测量：

- Recall@K：正确证据是否进入前 K 个候选；
- MRR/NDCG：正确证据是否排在前面；
- 引用正确率：引用是否支持回答；
- Groundedness：回答是否忠于证据；
- 拒答准确率：无证据时是否正确拒答；
- P95 延迟与单次成本。

评测集应来自真实业务问题，包含可回答问题、不可回答问题、冲突知识和权限受限问题。

## 7. 企业级难点

- OCR、复杂表格、多栏和图片理解；
- 权限必须在召回前生效；
- 多版本冲突和过期知识；
- 大规模异步索引与失败恢复；
- 模型、Embedding 和 Prompt 升级后的回归；
- 数据删除在索引、缓存和日志中的传播。

## 8. 推荐排查顺序

回答错误时依次检查：原文是否存在且有效、解析是否正确、正确块是否被召回、是否在融合或权限过滤中丢失、证据是否进入 Prompt、模型是否曲解、问题是否超出知识边界。


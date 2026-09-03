# Retrieval Eval Report

- dataset: `evals/datasets/retrieval_v1.jsonl`
- knowledge_base_id: `b2d70e40-02d1-4a78-af5a-22df85a82693`
- generated_at: 2026-09-03T13:52:03.952919+00:00
- app_version: 0.1.0
- dataset_sha256: `d4c4213e3cfcdcff1d04caf2b844539f8adecf6e659c36820f96672953a0f6b7`
- embedding: bge / BAAI/bge-small-zh-v1.5
- retrieval: top_k=6, candidate_k=20, min_score=0.01
- knowledge_base: AgentMentor BGE 验收知识库 (documents=7, active=7, ready=7, chunks=195, catalog_points=194)
- total: 30
- Recall@1: 0.5
- Recall@3: 0.6538
- Recall@6: 0.7308
- MRR: 0.5865
- Evidence sufficient accuracy: 0.7667
- Negative rejection accuracy: 1.0

## Evidence Gate Failures

### ret-007

- question: 资料未覆盖问题时系统应该如何回答？
- answerable: True
- evidence_sufficient: False
- supported_chunk_count: 0
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.01639344262295082

### ret-009

- question: 可信等级可以怎样影响检索排序？
- answerable: True
- evidence_sufficient: False
- supported_chunk_count: 0
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.01639344262295082

### ret-014

- question: SSE 问答流需要哪些终止事件？
- answerable: True
- evidence_sufficient: False
- supported_chunk_count: 0
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.01639344262295082

### ret-017

- question: 为什么 V1 不引入 Elasticsearch？
- answerable: True
- evidence_sufficient: False
- supported_chunk_count: 0
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.01639344262295082

### ret-018

- question: 为什么评测需要 Recall@K 和 MRR？
- answerable: True
- evidence_sufficient: False
- supported_chunk_count: 0
- top_document: 第 5 课：可信评分与报告
- top_score: 0.01639344262295082

### ret-020

- question: 单文档占比控制想避免什么问题？
- answerable: True
- evidence_sufficient: False
- supported_chunk_count: 0
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.01639344262295082

### ret-022

- question: PostgreSQL pgvector 在这个项目中有什么好处？
- answerable: True
- evidence_sufficient: False
- supported_chunk_count: 0
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.01639344262295082

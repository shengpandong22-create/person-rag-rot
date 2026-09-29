# Retrieval Eval Report

## Reproducibility

- git_commit: `744ef3b43b9fad5dce280a3a485d68c69dc860ca` (dirty=True)
- git_branch: `codex/eval-foundation-rebuild`
- dataset: `evals\datasets\retrieval_regression_v1.jsonl`
- dataset_sha256: `dc980d953d62bf939c6b5c64e366897c1e78957df0f928e6381aeaeece592df2`
- freeze_manifest_sha256: `None`
- app_version: 0.1.0
- generated_at: 2026-09-29T13:37:48.020049+00:00
- run_duration_ms: 28865.4821
- holdout_intact: True
- holdout_detail: intact: 19 cases, sha256=9f9d1dbb04df5147..., frozen_at=2026-09-19T06:25:25.284526+00:00

## Scope

- metrics_scope: graded_rows_only
- graded_rows: 30
- ungraded_rows: 0
- ground_truth_resolution: {'resolved': 20, 'absent': 10}
- ungraded 行仅作诊断，不进入下方 Recall/MRR。ground_truth_mode=keyword_fallback 表示标签未能解析到当前知识库，该行结论不可信，需先修标注。

## Configuration

- embedding: bge / BAAI/bge-small-zh-v1.5
- embedding_dimension: 512
- experiment_mode: vector-only
- query_strategy: original
- adjacent_filter_strategy: current
- candidate_expansion: none
- retrieval: top_k=6, candidate_k=20, min_score=0.013
- rrf_k: 60
- heuristic_weights: {'vector': 0.003, 'text': 0.004, 'lexical': 0.006}
- knowledge_base: AgentMentor BGE 验收知识库 (documents=7, active=7, ready=7, chunks=195, catalog_points=195)

## Metrics (graded rows only)

- total: 30
- Recall@1: 0.2
- Recall@3: 0.4
- Recall@6: 0.45
- MRR: 0.3017
- Full answerability accuracy: 0.8824
- Partial answerability accuracy: 0.3333
- Evidence sufficient accuracy: 0.7
- Negative rejection accuracy: 0.5
- Full acceptance rate: 0.8824
- Partial acceptance rate: 0.3333
- Partial boundary detection rate: 0.0
- None rejection rate: 0.5
- Evidence macro accuracy: 0.4608
- Evidence confusion matrix: {'full': {'full': 15, 'partial': 0, 'none': 2}, 'partial': {'full': 1, 'partial': 0, 'none': 2}, 'none': {'full': 5, 'partial': 0, 'none': 5}}
- Rejection by negative reason: {'in_domain_no_conclusion': 0.4, 'in_domain_value_missing': 1.0, 'out_of_scope': 0.5}
- Retrieval latency P50/P95 ms: 34.4894 / 48.2571
- Average candidate count: 6.0
- Candidate Recall@20: 0.8
- Pre-filter Recall@6: 0.6
- Post-filter Recall@6: 0.45
- Diversity filter drop rate: 0.34
- Failure category counts: {'adjacent_filter_miss': 2, 'candidate_recall_miss': 4, 'correct_rejection': 5, 'evidence_gate_rejection': 1, 'false_acceptance': 5, 'per_document_filter_miss': 1, 'ranking_cutoff_miss': 4}

## Evidence Gate Failures

### ret-004

- question: Java 后端转 AI Agent 开发为什么需要学习 RAG？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {'Java': 1, 'AI Agent': 0, 'RAG': 65}
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.6732817687606312

### ret-007

- question: 资料未覆盖问题时系统应该如何回答？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {'证据不足': 7, '不伪造引用': 0}
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.6401721453564092

### ret-013

- question: Prompt Injection 文档指令为什么不能覆盖系统规则？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 4
- diagnostic_keyword_coverage: {'Prompt Injection': 0, '系统规则': 0, '不可信数据': 0}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.604995846748352

### ret-018

- question: 为什么评测需要 Recall@K 和 MRR？
- answerability: partial
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {'Recall': 1, 'MRR': 0, '评测': 6}
- top_document: 第 5 课：可信评分与报告
- top_score: 0.6119930561783024

### ret-020

- question: 单文档占比控制想避免什么问题？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {'单文档': 0, '占比': 1, '多样性': 0}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.6044424772262573

### ret-022

- question: PostgreSQL pgvector 在这个项目中有什么好处？
- answerability: partial
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {'PostgreSQL': 3, 'pgvector': 6, '业务数据': 0}
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.5835944662335844

### ret-025

- question: 为什么测试环境不能误读真实 API Key？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 3
- diagnostic_keyword_coverage: {'测试环境': 0, 'API Key': 1, '安全': 7}
- top_document: 第 4 课：可恢复模拟面试工作流
- top_score: 0.6184144843569717

### ret-027

- question: 唐朝开元年间的具体盐税制度如何影响 RAG 系统设计？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 7 课：工程化专题 + 面试实战
- top_score: 0.4355433323655534

### ret-030

- question: Docker Desktop 4.82 的所有发布说明逐条是什么？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.5821845282426206

## Failure Attribution

- `ret-001`: candidate_recall_miss (decision=accept, rank=None)
- `ret-002`: ranking_cutoff_miss (decision=accept, rank=None)
- `ret-003`: per_document_filter_miss (decision=accept, rank=None)
- `ret-004`: false_acceptance (decision=accept, rank=1)
- `ret-005`: adjacent_filter_miss (decision=accept, rank=None)
- `ret-007`: ranking_cutoff_miss (decision=reject, rank=None)
- `ret-009`: correct_rejection (decision=reject, rank=None)
- `ret-011`: candidate_recall_miss (decision=accept, rank=None)
- `ret-013`: false_acceptance (decision=accept, rank=None)
- `ret-014`: correct_rejection (decision=reject, rank=None)
- `ret-015`: candidate_recall_miss (decision=accept, rank=None)
- `ret-016`: adjacent_filter_miss (decision=accept, rank=None)
- `ret-017`: correct_rejection (decision=reject, rank=None)
- `ret-018`: candidate_recall_miss (decision=reject, rank=None)
- `ret-020`: evidence_gate_rejection (decision=reject, rank=1)
- `ret-022`: ranking_cutoff_miss (decision=reject, rank=None)
- `ret-023`: ranking_cutoff_miss (decision=accept, rank=None)
- `ret-025`: false_acceptance (decision=accept, rank=2)
- `ret-027`: false_acceptance (decision=accept, rank=None)
- `ret-028`: correct_rejection (decision=reject, rank=None)
- `ret-029`: correct_rejection (decision=reject, rank=None)
- `ret-030`: false_acceptance (decision=accept, rank=None)

# Retrieval Eval Report

## Reproducibility

- git_commit: `822c086f403d03bebb427890107ffae109e81a7e` (dirty=False)
- git_branch: `codex/eval-foundation-rebuild`
- dataset: `evals\datasets\retrieval_holdout_v1.jsonl`
- dataset_sha256: `9f9d1dbb04df5147bc7b7f61998f74302d5e45ec8138e4fd7452bd48fadb37c9`
- freeze_manifest_sha256: `96a4851a1f1d2333f005771c010aa4f79b414dca46a3d5d4fc9f94ef50173c43`
- app_version: 0.1.0
- generated_at: 2026-09-26T10:51:00.789882+00:00
- run_duration_ms: 35117.8121
- holdout_intact: True
- holdout_detail: intact: 19 cases, sha256=9f9d1dbb04df5147..., frozen_at=2026-09-19T06:25:25.284526+00:00

## Scope

- metrics_scope: graded_rows_only
- graded_rows: 19
- ungraded_rows: 0
- ground_truth_resolution: {'absent': 10, 'resolved': 9}
- ungraded 行仅作诊断，不进入下方 Recall/MRR。ground_truth_mode=keyword_fallback 表示标签未能解析到当前知识库，该行结论不可信，需先修标注。

## Configuration

- embedding: bge / BAAI/bge-small-zh-v1.5
- embedding_dimension: 512
- experiment_mode: vector-only
- retrieval: top_k=6, candidate_k=20, min_score=0.013
- rrf_k: 60
- heuristic_weights: {'vector': 0.003, 'text': 0.004, 'lexical': 0.006}
- knowledge_base: AgentMentor BGE 验收知识库 (documents=7, active=7, ready=7, chunks=195, catalog_points=195)

## Metrics (graded rows only)

- total: 19
- Recall@1: 0.3333
- Recall@3: 0.5556
- Recall@6: 0.5556
- MRR: 0.4259
- Full answerability accuracy: 0.8889
- Partial answerability accuracy: 0.0
- Evidence sufficient accuracy: 0.5789
- Negative rejection accuracy: 0.3
- Rejection by negative reason: {'false_premise': 0.3333, 'in_domain_no_conclusion': 0.0, 'in_domain_value_missing': 0.25, 'out_of_range_implementation': 0.0, 'version_not_released': 1.0}
- Retrieval latency P50/P95 ms: 50.0478 / 34128.832
- Average candidate count: 6.0

## Evidence Gate Failures

### ho-neg-002

- question: 为什么本项目用 Redis 保存面试工作流的 checkpoint？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 6
- diagnostic_keyword_coverage: {'Redis': 0, 'checkpoint': 27, '持久化': 8}
- top_document: 第 4 课：可恢复模拟面试工作流
- top_score: 0.7286338210105896

### ho-neg-003

- question: 为什么本项目用 Celery 处理文档摄入任务？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {'Celery': 0, '摄入': 1, '任务队列': 0}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.595339024344742

### ho-neg-004

- question: 本项目当前使用的 pgvector 精确版本号是多少？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {'pgvector': 6, '版本号': 3}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.5533331632614136

### ho-neg-005

- question: BGE reranker 的 P95 延迟是多少毫秒？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {'reranker': 4, 'P95': 0, '延迟': 1}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.5152663877447622

### ho-neg-006

- question: Cross-Encoder 精排相比 RRF 带来了多少 Recall 提升？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 5
- diagnostic_keyword_coverage: {'Cross-Encoder': 0, 'Recall': 1, '提升': 2}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.6116052501436929

### ho-neg-009

- question: 当前系统支持哪些 PDF OCR 能力？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {'OCR': 6, 'PDF': 6, '扫描件': 1}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.6522698428148324

### ho-neg-010

- question: 检索时如何按资料可信等级过滤？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {'可信等级': 0, '过滤': 2, '检索': 86}
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.6187478261066545

### ho-pos-004

- question: 文档生命周期中一共有哪些状态，流入和流出分别由什么驱动？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {'状态机': 11, '生命周期': 0, '就绪': 0}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.5189119268112236

## Failure Attribution

- `ho-neg-001`: correct_rejection (decision=reject, rank=None)
- `ho-neg-002`: false_acceptance (decision=accept, rank=1)
- `ho-neg-003`: false_acceptance (decision=accept, rank=1)
- `ho-neg-004`: false_acceptance (decision=accept, rank=1)
- `ho-neg-005`: false_acceptance (decision=accept, rank=1)
- `ho-neg-006`: false_acceptance (decision=accept, rank=5)
- `ho-neg-007`: correct_rejection (decision=reject, rank=2)
- `ho-neg-008`: correct_rejection (decision=reject, rank=None)
- `ho-neg-009`: false_acceptance (decision=accept, rank=1)
- `ho-pos-001`: retrieval_miss (decision=accept, rank=None)
- `ho-pos-002`: retrieval_miss (decision=accept, rank=None)
- `ho-neg-010`: false_acceptance (decision=accept, rank=3)
- `ho-pos-004`: evidence_gate_rejection (decision=reject, rank=3)
- `ho-pos-005`: retrieval_miss (decision=accept, rank=None)
- `ho-pos-010`: retrieval_miss (decision=accept, rank=None)

# Retrieval Eval Report

## Reproducibility

- git_commit: `021a4f7fe0fe10b2930f3870f93ba682cac3b894` (dirty=False)
- git_branch: `codex/eval-foundation-rebuild`
- dataset: `evals\datasets\retrieval_relation_value_blind_v1.jsonl`
- dataset_sha256: `3b450912e3786029297e482efdae0548a8b941b7c83bcaa23a198ca601ea4a09`
- freeze_manifest_sha256: `None`
- app_version: 0.1.0
- generated_at: 2026-10-01T11:21:55.233932+00:00
- run_duration_ms: 31522.2409
- holdout_intact: True
- holdout_detail: intact: 19 cases, sha256=9f9d1dbb04df5147..., frozen_at=2026-09-19T06:25:25.284526+00:00

## Scope

- metrics_scope: graded_rows_only
- graded_rows: 16
- ungraded_rows: 0
- ground_truth_resolution: {'resolved': 10, 'absent': 6}
- ungraded 行仅作诊断，不进入下方 Recall/MRR。ground_truth_mode=keyword_fallback 表示标签未能解析到当前知识库，该行结论不可信，需先修标注。

## Configuration

- embedding: bge / BAAI/bge-small-zh-v1.5
- embedding_dimension: 512
- experiment_mode: vector-only
- query_strategy: original
- adjacent_filter_strategy: current
- candidate_expansion: heading-shadow
- supplemental_consumption: none
- supplemental_k: 1
- retrieval: top_k=6, candidate_k=20, min_score=0.013
- rrf_k: 60
- heuristic_weights: {'vector': 0.003, 'text': 0.004, 'lexical': 0.006}
- knowledge_base: AgentMentor BGE 验收知识库 (documents=7, active=7, ready=7, chunks=195, catalog_points=195)

## Metrics (graded rows only)

- total: 16
- Recall@1: 0.3
- Recall@3: 0.5
- Recall@6: 0.7
- MRR: 0.44
- Full answerability accuracy: 1.0
- Partial answerability accuracy: 0.0
- Evidence sufficient accuracy: 0.6875
- Negative rejection accuracy: 0.1667
- Full acceptance rate: 1.0
- Partial acceptance rate: 0.0
- Partial boundary detection rate: 0.0
- None rejection rate: 0.1667
- Evidence macro accuracy: 0.0
- Evidence confusion matrix: {'full': {'full': 0, 'partial': 0, 'none': 0}, 'partial': {'full': 0, 'partial': 0, 'none': 0}, 'none': {'full': 0, 'partial': 0, 'none': 0}}
- Rejection by negative reason: {'false_premise': 0.0, 'in_domain_value_missing': 0.3333}
- Retrieval latency P50/P95 ms: 129.2201 / 29511.9559
- Average candidate count: 6.0
- Candidate Recall@20: 0.9
- Pre-filter Recall@6: 0.7
- Post-filter Recall@6: 0.7
- Primary@6 + supplemental@1: 0.9
- Primary@6 + supplemental@3: 0.9
- Primary@6 + supplemental@6: 0.9
- Primary@6 + supplemental@20: 0.9
- Average supplemental candidate count: 10.0
- Supplemental trigger count/rate: 0 / 0.0
- Average consumed supplemental count: 0.0
- Gate promotions/demotions: 0 / 0
- Consumed relevant count/per trigger: 0 / 0.0
- Diversity filter drop rate: 0.3344
- Failure category counts: {'candidate_recall_miss': 1, 'correct_rejection': 1, 'false_acceptance': 5, 'per_document_filter_miss': 2}

## Evidence Gate Failures

### rvb-s-004

- question: 知识目录同步在生产环境的平均耗时是多少毫秒？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 1 课：项目全景与架构地图
- top_score: 0.5020707546430385

### rvb-t-003

- question: 解析格式对照表规定 PDF 最大允许多少页？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.5925443172454834

### rvb-t-004

- question: 三种评分状态对画像影响表规定 REVIEW_PENDING 保留 30 天，对吗？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 4
- diagnostic_keyword_coverage: {}
- top_document: 第 5 课：可信评分与报告
- top_score: 0.7154872587032772

### rvb-b-003

- question: RRF 具体计算示例证明线上 P95 检索延迟是 32.3 毫秒吗？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 3
- diagnostic_keyword_coverage: {}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.5785742057219632

### rvb-b-004

- question: 中文词汇化门禁是否保证召回准确率达到 18%？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.5245555922653927

## Failure Attribution

- `rvb-s-001`: candidate_recall_miss (decision=accept, rank=None)
- `rvb-s-002`: per_document_filter_miss (decision=accept, rank=None)
- `rvb-s-004`: false_acceptance (decision=accept, rank=None)
- `rvb-t-001`: per_document_filter_miss (decision=accept, rank=None)
- `rvb-t-003`: false_acceptance (decision=accept, rank=None)
- `rvb-t-004`: false_acceptance (decision=accept, rank=None)
- `rvb-c-004`: correct_rejection (decision=reject, rank=None)
- `rvb-b-003`: false_acceptance (decision=accept, rank=None)
- `rvb-b-004`: false_acceptance (decision=accept, rank=None)

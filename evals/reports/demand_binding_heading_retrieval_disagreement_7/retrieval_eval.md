# Retrieval Eval Report

## Reproducibility

- git_commit: `6ffe76d87e45dca10b0b7ba8c5f75d0a381cf877` (dirty=True)
- git_branch: `codex/eval-foundation-rebuild`
- dataset: `evals\datasets\retrieval_demand_binding_development_v1.jsonl`
- dataset_sha256: `c0f501397764d9c42d006d7eec6ba6dbcd36248fd01219f1072b2a0e3dcff3df`
- freeze_manifest_sha256: `9e5ba0745ba9c93ad68afa4f5204cf909b7d8d8e81758d1c99002fe210893884`
- app_version: 0.1.0
- generated_at: 2026-10-01T08:31:59.211432+00:00
- run_duration_ms: 26804.5127
- holdout_intact: True
- holdout_detail: intact: 19 cases, sha256=9f9d1dbb04df5147..., frozen_at=2026-09-19T06:25:25.284526+00:00

## Scope

- metrics_scope: graded_rows_only
- graded_rows: 15
- ungraded_rows: 0
- ground_truth_resolution: {'resolved': 10, 'absent': 5}
- ungraded 行仅作诊断，不进入下方 Recall/MRR。ground_truth_mode=keyword_fallback 表示标签未能解析到当前知识库，该行结论不可信，需先修标注。

## Configuration

- embedding: bge / BAAI/bge-small-zh-v1.5
- embedding_dimension: 512
- experiment_mode: vector-only
- query_strategy: original
- adjacent_filter_strategy: current
- candidate_expansion: heading-shadow
- supplemental_consumption: retrieval-disagreement
- supplemental_k: 7
- retrieval: top_k=6, candidate_k=20, min_score=0.013
- rrf_k: 60
- heuristic_weights: {'vector': 0.003, 'text': 0.004, 'lexical': 0.006}
- knowledge_base: AgentMentor BGE 验收知识库 (documents=7, active=7, ready=7, chunks=195, catalog_points=195)

## Metrics (graded rows only)

- total: 15
- Recall@1: 0.4
- Recall@3: 0.4
- Recall@6: 0.6
- MRR: 0.45
- Full answerability accuracy: 1.0
- Partial answerability accuracy: 0.0
- Evidence sufficient accuracy: 0.8667
- Negative rejection accuracy: 0.6
- Full acceptance rate: 1.0
- Partial acceptance rate: 0.0
- Partial boundary detection rate: 0.0
- None rejection rate: 0.6
- Evidence macro accuracy: 0.0
- Evidence confusion matrix: {'full': {'full': 0, 'partial': 0, 'none': 0}, 'partial': {'full': 0, 'partial': 0, 'none': 0}, 'none': {'full': 0, 'partial': 0, 'none': 0}}
- Rejection by negative reason: {'false_premise': 1.0, 'in_domain_value_missing': 0.5}
- Retrieval latency P50/P95 ms: 46.9543 / 26165.488
- Average candidate count: 8.6
- Candidate Recall@20: 0.6
- Pre-filter Recall@6: 0.6
- Post-filter Recall@6: 0.6
- Primary@6 + supplemental@1: 0.8
- Primary@6 + supplemental@3: 0.9
- Primary@6 + supplemental@6: 0.9
- Primary@6 + supplemental@20: 1.0
- Average supplemental candidate count: 9.7
- Supplemental trigger count/rate: 9 / 0.6
- Average consumed supplemental count: 2.6
- Gate promotions/demotions: 0 / 0
- Consumed relevant count/per trigger: 4 / 0.4444
- Diversity filter drop rate: 0.4033
- Failure category counts: {'candidate_recall_miss': 4, 'correct_rejection': 3, 'false_acceptance': 2}

## Evidence Gate Failures

### db-ex-003

- question: Reviewer 的生产可用性 SLA 是否精确承诺为 99.9%？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 3
- diagnostic_keyword_coverage: {}
- top_document: 第 5 课：可信评分与报告
- top_score: 0.5776361227035522

### db-ta-003

- question: 三种评分状态对画像影响表是否给出了 30 天保留期？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {}
- top_document: 第 5 课：可信评分与报告
- top_score: 0.6704838675548963

## Failure Attribution

- `db-ex-002`: candidate_recall_miss (decision=accept, rank=None)
- `db-ex-003`: false_acceptance (decision=accept, rank=None)
- `db-un-002`: candidate_recall_miss (decision=accept, rank=None)
- `db-un-003`: correct_rejection (decision=reject, rank=None)
- `db-ra-002`: candidate_recall_miss (decision=accept, rank=None)
- `db-ra-003`: correct_rejection (decision=reject, rank=None)
- `db-ta-002`: candidate_recall_miss (decision=accept, rank=None)
- `db-ta-003`: false_acceptance (decision=accept, rank=None)
- `db-cr-003`: correct_rejection (decision=reject, rank=None)

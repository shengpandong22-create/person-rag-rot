# Retrieval Eval Report

## Reproducibility

- git_commit: `357fbc43b7b959845796b22787dde2a803d92ee8` (dirty=False)
- git_branch: `codex/eval-foundation-rebuild`
- dataset: `evals\datasets\retrieval_relation_value_development_v1.jsonl`
- dataset_sha256: `9156164ba289b2407b104c85a717d58149e8862ef5e2ffba6d4aedad9b20173f`
- freeze_manifest_sha256: `18154e34e6d833f593a01cf1f693cc6bdd13937e9b2364033fd3b67687ffc976`
- app_version: 0.1.0
- generated_at: 2026-10-01T10:53:36.261124+00:00
- run_duration_ms: 25989.2578
- holdout_intact: True
- holdout_detail: intact: 19 cases, sha256=9f9d1dbb04df5147..., frozen_at=2026-09-19T06:25:25.284526+00:00

## Scope

- metrics_scope: graded_rows_only
- graded_rows: 12
- ungraded_rows: 0
- ground_truth_resolution: {'resolved': 8, 'absent': 4}
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

- total: 12
- Recall@1: 0.625
- Recall@3: 0.75
- Recall@6: 0.75
- MRR: 0.6667
- Full answerability accuracy: 0.875
- Partial answerability accuracy: 0.0
- Evidence sufficient accuracy: 0.75
- Negative rejection accuracy: 0.5
- Full acceptance rate: 0.875
- Partial acceptance rate: 0.0
- Partial boundary detection rate: 0.0
- None rejection rate: 0.5
- Evidence macro accuracy: 0.0
- Evidence confusion matrix: {'full': {'full': 0, 'partial': 0, 'none': 0}, 'partial': {'full': 0, 'partial': 0, 'none': 0}, 'none': {'full': 0, 'partial': 0, 'none': 0}}
- Rejection by negative reason: {'false_premise': 1.0, 'in_domain_value_missing': 0.3333}
- Retrieval latency P50/P95 ms: 50.868 / 25459.9646
- Average candidate count: 6.0
- Candidate Recall@20: 1.0
- Pre-filter Recall@6: 0.75
- Post-filter Recall@6: 0.75
- Primary@6 + supplemental@1: 0.875
- Primary@6 + supplemental@3: 0.875
- Primary@6 + supplemental@6: 0.875
- Primary@6 + supplemental@20: 0.875
- Average supplemental candidate count: 6.875
- Supplemental trigger count/rate: 0 / 0.0
- Average consumed supplemental count: 0.0
- Gate promotions/demotions: 0 / 0
- Consumed relevant count/per trigger: 0 / 0.0
- Diversity filter drop rate: 0.4
- Failure category counts: {'correct_rejection': 2, 'evidence_gate_rejection': 1, 'false_acceptance': 2, 'per_document_filter_miss': 2}

## Evidence Gate Failures

### rv-s-003

- question: RRF 生产吞吐关系对应的实测 QPS 数值是多少？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 6
- diagnostic_keyword_coverage: {}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.5755248069763184

### rv-t-003

- question: 三种评分状态影响表给出的 REVIEW_PENDING 最长保留天数是多少？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {}
- top_document: 第 5 课：可信评分与报告
- top_score: 0.6689278680725188

### rv-c-002

- question: 渐进更新代码给学习率设置的硬上限是多少？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {}
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.6298349344927151

## Failure Attribution

- `rv-s-003`: false_acceptance (decision=accept, rank=None)
- `rv-t-001`: per_document_filter_miss (decision=accept, rank=None)
- `rv-t-002`: per_document_filter_miss (decision=accept, rank=None)
- `rv-t-003`: false_acceptance (decision=accept, rank=None)
- `rv-c-002`: evidence_gate_rejection (decision=reject, rank=1)
- `rv-c-003`: correct_rejection (decision=reject, rank=None)
- `rv-b-003`: correct_rejection (decision=reject, rank=None)

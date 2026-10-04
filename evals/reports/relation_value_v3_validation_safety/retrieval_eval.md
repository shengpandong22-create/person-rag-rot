# Retrieval Eval Report

## Reproducibility

- git_commit: `unknown` (dirty=False)
- git_branch: `unknown`
- dataset: `evals/datasets/retrieval_validation_v1.jsonl`
- dataset_sha256: `4ab6e481a792a60f612e6b1f29efaa7397371561662991eb682d3b72b617d441`
- freeze_manifest_sha256: `e04fd574249bc4cc72a7e7c8a5eb9e79cc3341d9e66bad5c78e0b4fbe82abd32`
- app_version: 0.1.0
- generated_at: 2026-10-04T07:42:03.895513+00:00
- run_duration_ms: 18982.5749
- holdout_intact: True
- holdout_detail: intact: 19 cases, sha256=9f9d1dbb04df5147..., frozen_at=2026-09-19T06:25:25.284526+00:00

## Scope

- metrics_scope: graded_rows_only
- graded_rows: 22
- ungraded_rows: 0
- ground_truth_resolution: {'resolved': 17, 'absent': 5}
- ungraded 行仅作诊断，不进入下方 Recall/MRR。ground_truth_mode=keyword_fallback 表示标签未能解析到当前知识库，该行结论不可信，需先修标注。

## Configuration

- embedding: bge / BAAI/bge-small-zh-v1.5
- embedding_dimension: 512
- experiment_mode: vector-only
- query_strategy: original
- adjacent_filter_strategy: current
- candidate_expansion: none
- supplemental_consumption: none
- supplemental_k: 1
- retrieval: top_k=6, candidate_k=20, min_score=0.013
- rrf_k: 60
- heuristic_weights: {'vector': 0.003, 'text': 0.004, 'lexical': 0.006}
- knowledge_base: AgentMentor BGE 验收知识库 (documents=7, active=7, ready=7, chunks=195, catalog_points=195)

## Metrics (graded rows only)

- total: 22
- Recall@1: 0.3529
- Recall@3: 0.5294
- Recall@6: 0.7059
- MRR: 0.4853
- Full answerability accuracy: 1.0
- Partial answerability accuracy: 1.0
- Evidence sufficient accuracy: 1.0
- Negative rejection accuracy: 1.0
- Full acceptance rate: 1.0
- Partial acceptance rate: 1.0
- Partial boundary detection rate: 0.0
- None rejection rate: 1.0
- Evidence macro accuracy: 0.0
- Evidence confusion matrix: {'full': {'full': 0, 'partial': 0, 'none': 0}, 'partial': {'full': 0, 'partial': 0, 'none': 0}, 'none': {'full': 0, 'partial': 0, 'none': 0}}
- Rejection by negative reason: {'conflicting_sources': 1.0, 'false_premise': 1.0, 'in_domain_no_conclusion': 1.0, 'in_domain_value_missing': 1.0}
- Retrieval latency P50/P95 ms: 24.5834 / 32.6679
- Average candidate count: 6.0
- Candidate Recall@20: 0.8824
- Pre-filter Recall@6: 0.8235
- Post-filter Recall@6: 0.7059
- Primary@6 + supplemental@1: 0.7059
- Primary@6 + supplemental@3: 0.7059
- Primary@6 + supplemental@6: 0.7059
- Primary@6 + supplemental@20: 0.7059
- Average supplemental candidate count: 0.0
- Supplemental trigger count/rate: 0 / 0.0
- Average consumed supplemental count: 0.0
- Gate promotions/demotions: 0 / 0
- Consumed relevant count/per trigger: 0 / 0.0
- Diversity filter drop rate: 0.3432
- Failure category counts: {'candidate_recall_miss': 2, 'correct_rejection': 5, 'partial_answer_boundary': 2, 'per_document_filter_miss': 3}

## Failure Attribution

- `va-pt-001`: partial_answer_boundary (decision=accept, rank=1)
- `va-pt-002`: partial_answer_boundary (decision=accept, rank=1)
- `va-neg-001`: correct_rejection (decision=reject, rank=1)
- `va-neg-002`: correct_rejection (decision=reject, rank=1)
- `va-neg-003`: correct_rejection (decision=reject, rank=4)
- `va-neg-004`: correct_rejection (decision=reject, rank=3)
- `va-neg-005`: correct_rejection (decision=reject, rank=None)
- `va-pos-002`: per_document_filter_miss (decision=accept, rank=None)
- `va-pos-003`: per_document_filter_miss (decision=accept, rank=None)
- `va-pos-004`: candidate_recall_miss (decision=accept, rank=None)
- `va-pos-010`: candidate_recall_miss (decision=accept, rank=None)
- `va-pos-014`: per_document_filter_miss (decision=accept, rank=None)

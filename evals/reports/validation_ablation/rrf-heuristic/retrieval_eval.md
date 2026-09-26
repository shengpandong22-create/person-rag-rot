# Retrieval Eval Report

## Reproducibility

- git_commit: `d0c9061b9cc02f1986c3a7f41ee2042a2de64371` (dirty=True)
- git_branch: `codex/eval-foundation-rebuild`
- dataset: `evals\datasets\retrieval_validation_v1.jsonl`
- dataset_sha256: `4ab6e481a792a60f612e6b1f29efaa7397371561662991eb682d3b72b617d441`
- freeze_manifest_sha256: `e04fd574249bc4cc72a7e7c8a5eb9e79cc3341d9e66bad5c78e0b4fbe82abd32`
- app_version: 0.1.0
- generated_at: 2026-09-26T10:43:44.138094+00:00
- run_duration_ms: 8294.271
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
- experiment_mode: rrf-heuristic
- retrieval: top_k=6, candidate_k=20, min_score=0.013
- rrf_k: 60
- heuristic_weights: {'vector': 0.003, 'text': 0.004, 'lexical': 0.006}
- knowledge_base: AgentMentor BGE 验收知识库 (documents=7, active=7, ready=7, chunks=195, catalog_points=195)

## Metrics (graded rows only)

- total: 22
- Recall@1: 0.1765
- Recall@3: 0.5294
- Recall@6: 0.7059
- MRR: 0.3647
- Full answerability accuracy: 1.0
- Partial answerability accuracy: 1.0
- Evidence sufficient accuracy: 1.0
- Negative rejection accuracy: 1.0
- Rejection by negative reason: {'conflicting_sources': 1.0, 'false_premise': 1.0, 'in_domain_no_conclusion': 1.0, 'in_domain_value_missing': 1.0}
- Retrieval latency P50/P95 ms: 67.9822 / 118.7112
- Average candidate count: 6.0

## Failure Attribution

- `va-pt-001`: retrieval_miss (decision=accept, rank=None)
- `va-pt-002`: partial_answer_boundary (decision=accept, rank=2)
- `va-neg-001`: correct_rejection (decision=reject, rank=2)
- `va-neg-002`: correct_rejection (decision=reject, rank=2)
- `va-neg-003`: correct_rejection (decision=reject, rank=1)
- `va-neg-004`: correct_rejection (decision=reject, rank=None)
- `va-neg-005`: correct_rejection (decision=reject, rank=None)
- `va-pos-002`: retrieval_miss (decision=accept, rank=None)
- `va-pos-004`: retrieval_miss (decision=accept, rank=None)
- `va-pos-010`: retrieval_miss (decision=accept, rank=None)
- `va-pos-012`: retrieval_miss (decision=accept, rank=None)

# Retrieval Eval Report

## Reproducibility

- git_commit: `b61ea5a823a7c244a189c46709f87065801145fe` (dirty=False)
- git_branch: `codex/eval-foundation-rebuild`
- dataset: `evals\datasets\retrieval_quota4_acceptance_v1.jsonl`
- dataset_sha256: `da6f8a563a8fa6b1b66ecc6868e0626797885892282885b7daa883cd8f9d6f1b`
- freeze_manifest_sha256: `fad8dbc00a69c1c6beb7536884e275497f5d6472c10f06bca1c0c76dd1d86615`
- app_version: 0.1.0
- generated_at: 2026-09-29T12:11:51.553869+00:00
- run_duration_ms: 32678.8894
- holdout_intact: True
- holdout_detail: intact: 19 cases, sha256=9f9d1dbb04df5147..., frozen_at=2026-09-19T06:25:25.284526+00:00

## Scope

- metrics_scope: graded_rows_only
- graded_rows: 18
- ungraded_rows: 0
- ground_truth_resolution: {'resolved': 14, 'absent': 4}
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

- total: 18
- Recall@1: 0.3571
- Recall@3: 0.4286
- Recall@6: 0.5
- MRR: 0.3988
- Full answerability accuracy: 0.9167
- Partial answerability accuracy: 0.5
- Evidence sufficient accuracy: 0.7222
- Negative rejection accuracy: 0.25
- Full acceptance rate: 0.9167
- Partial acceptance rate: 0.5
- Partial boundary detection rate: 0.0
- None rejection rate: 0.25
- Evidence macro accuracy: 0.3889
- Evidence confusion matrix: {'full': {'full': 11, 'partial': 0, 'none': 1}, 'partial': {'full': 1, 'partial': 0, 'none': 1}, 'none': {'full': 3, 'partial': 0, 'none': 1}}
- Rejection by negative reason: {'false_premise': 0.0, 'in_domain_no_conclusion': 1.0, 'in_domain_value_missing': 0.0}
- Retrieval latency P50/P95 ms: 45.4311 / 31951.0801
- Average candidate count: 6.0
- Candidate Recall@20: 0.7857
- Pre-filter Recall@6: 0.6429
- Post-filter Recall@6: 0.5
- Diversity filter drop rate: 0.2139
- Failure category counts: {'adjacent_filter_miss': 2, 'candidate_recall_miss': 3, 'correct_rejection': 1, 'evidence_gate_rejection': 1, 'false_acceptance': 3, 'per_document_filter_miss': 1, 'ranking_cutoff_miss': 1}

## Evidence Gate Failures

### q4a-pos-010

- question: 重复提交答案时，Idempotency-Key 查询这一层具体先检查什么，又返回什么？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {'Idempotency-Key': 3, '已有提交': 0, '重复副作用': 0}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.6662368774414062

### q4a-pt-002

- question: 为什么模拟面试要支持断点重连，并且系统承诺离线多少小时后仍能无损恢复？
- answerability: partial
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {'断点重连': 0, '离线': 1, '小时': 1}
- top_document: 第 4 课：可恢复模拟面试工作流
- top_score: 0.6684200365293016

### q4a-neg-001

- question: 当前系统把动态子知识点硬限制为最多 128 个，这个阈值为什么是 128？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {'动态子知识点': 1, '128': 0, '阈值': 5}
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.5450860261917114

### q4a-neg-002

- question: 文档摄入完成后，知识目录同步任务的实测 P95 延迟是多少毫秒？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {'知识目录': 8, 'P95': 0, '毫秒': 2}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.5442393369389409

### q4a-neg-004

- question: 生产环境现已启用 Kafka 来保证评分事件和画像更新最终一致，请说明 topic 配置。
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {'Kafka': 0, '评分事件': 0, 'topic': 3}
- top_document: 第 7 课：工程化专题 + 面试实战
- top_score: 0.5942593812942547

## Failure Attribution

- `q4a-pos-004`: adjacent_filter_miss (decision=accept, rank=None)
- `q4a-pos-006`: per_document_filter_miss (decision=accept, rank=None)
- `q4a-pos-007`: adjacent_filter_miss (decision=accept, rank=None)
- `q4a-pos-009`: candidate_recall_miss (decision=accept, rank=None)
- `q4a-pos-010`: ranking_cutoff_miss (decision=reject, rank=None)
- `q4a-pos-011`: candidate_recall_miss (decision=accept, rank=None)
- `q4a-pt-001`: candidate_recall_miss (decision=accept, rank=None)
- `q4a-pt-002`: evidence_gate_rejection (decision=reject, rank=1)
- `q4a-neg-001`: false_acceptance (decision=accept, rank=6)
- `q4a-neg-002`: false_acceptance (decision=accept, rank=1)
- `q4a-neg-003`: correct_rejection (decision=reject, rank=None)
- `q4a-neg-004`: false_acceptance (decision=accept, rank=None)

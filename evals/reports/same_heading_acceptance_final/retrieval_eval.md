# Retrieval Eval Report

## Reproducibility

- git_commit: `82985a7d5ca33b883392efc30b2c5641c1613055` (dirty=False)
- git_branch: `codex/eval-foundation-rebuild`
- dataset: `evals\datasets\retrieval_same_heading_acceptance_v1.jsonl`
- dataset_sha256: `dce0fafd51b499ac050e183be8897d0f74a3c6809aad29b99951b45e45f4814e`
- freeze_manifest_sha256: `e45ec664f3ce2386fe97c83bdfbc5bd437cf17319e24a836120ad10c954062c2`
- app_version: 0.1.0
- generated_at: 2026-09-29T13:27:45.938062+00:00
- run_duration_ms: 24637.1005
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
- query_strategy: original
- adjacent_filter_strategy: same-heading
- retrieval: top_k=6, candidate_k=20, min_score=0.013
- rrf_k: 60
- heuristic_weights: {'vector': 0.003, 'text': 0.004, 'lexical': 0.006}
- knowledge_base: AgentMentor BGE 验收知识库 (documents=7, active=7, ready=7, chunks=195, catalog_points=195)

## Metrics (graded rows only)

- total: 18
- Recall@1: 0.3571
- Recall@3: 0.4286
- Recall@6: 0.4286
- MRR: 0.3929
- Full answerability accuracy: 0.75
- Partial answerability accuracy: 0.5
- Evidence sufficient accuracy: 0.6667
- Negative rejection accuracy: 0.5
- Full acceptance rate: 0.75
- Partial acceptance rate: 0.5
- Partial boundary detection rate: 0.0
- None rejection rate: 0.5
- Evidence macro accuracy: 0.4167
- Evidence confusion matrix: {'full': {'full': 9, 'partial': 0, 'none': 3}, 'partial': {'full': 1, 'partial': 0, 'none': 1}, 'none': {'full': 2, 'partial': 0, 'none': 2}}
- Rejection by negative reason: {'false_premise': 0.5, 'in_domain_no_conclusion': 1.0, 'in_domain_value_missing': 0.0}
- Retrieval latency P50/P95 ms: 33.2261 / 24062.5944
- Average candidate count: 6.0
- Candidate Recall@20: 0.7143
- Pre-filter Recall@6: 0.5
- Post-filter Recall@6: 0.4286
- Diversity filter drop rate: 0.375
- Failure category counts: {'candidate_recall_miss': 4, 'correct_rejection': 2, 'false_acceptance': 2, 'per_document_filter_miss': 4}

## Evidence Gate Failures

### sha-pos-003

- question: 资料总结的六个项目亮点分别体现了哪些不只是调用大模型的工程能力？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {'亮点': 2, '工程能力': 0, '可信': 70}
- top_document: 第 7 课：工程化专题 + 面试实战
- top_score: 0.5642404556274414

### sha-pos-008

- question: 中文全文查询如何构造匹配和排序，为什么不能只照搬英文分词方式？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {'全文查询': 0, '中文': 3, 'ts_rank': 4}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.6092027425765991

### sha-pos-011

- question: 评分复核路由会根据哪些确定性条件产生 review reasons？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {'review reasons': 0, '置信度': 4, '分差': 4}
- top_document: 第 5 课：可信评分与报告
- top_score: 0.706947645752062

### sha-pt-001

- question: 面试状态从 created 到 completed 如何流转，并且每个节点失败后固定重试几次？
- answerability: partial
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {'created': 4, 'completed': 2, '重试次数': 0}
- top_document: 第 4 课：可恢复模拟面试工作流
- top_score: 0.7224780321121216

### sha-neg-001

- question: 当前向量查询使用的 BGE tokenizer 精确版本号和 vocabulary hash 分别是什么？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {'tokenizer': 0, '版本号': 3, 'vocabulary hash': 0}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.5952438598580527

### sha-neg-002

- question: 系统为面试 checkpoint 配置的 Redis TTL 是多少分钟？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 6
- diagnostic_keyword_coverage: {'Redis': 0, 'TTL': 0, 'checkpoint': 27}
- top_document: 第 4 课：可恢复模拟面试工作流
- top_score: 0.6659559209929684

## Failure Attribution

- `sha-pos-003`: per_document_filter_miss (decision=reject, rank=None)
- `sha-pos-005`: per_document_filter_miss (decision=accept, rank=None)
- `sha-pos-007`: candidate_recall_miss (decision=accept, rank=None)
- `sha-pos-008`: per_document_filter_miss (decision=reject, rank=None)
- `sha-pos-009`: candidate_recall_miss (decision=accept, rank=None)
- `sha-pos-011`: per_document_filter_miss (decision=reject, rank=None)
- `sha-pt-001`: candidate_recall_miss (decision=reject, rank=None)
- `sha-pt-002`: candidate_recall_miss (decision=accept, rank=None)
- `sha-neg-001`: false_acceptance (decision=accept, rank=None)
- `sha-neg-002`: false_acceptance (decision=accept, rank=2)
- `sha-neg-003`: correct_rejection (decision=reject, rank=None)
- `sha-neg-004`: correct_rejection (decision=reject, rank=None)

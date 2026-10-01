# Retrieval Eval Report

## Reproducibility

- git_commit: `00e5a8bb93860bfc3a2261a8020c72ef4f513606` (dirty=True)
- git_branch: `codex/eval-foundation-rebuild`
- dataset: `evals\datasets\retrieval_trigger_development_v1.jsonl`
- dataset_sha256: `588d1b23c1932df51157f1f786a96c5e70b6cc3769c75be2f463235fe136b0bc`
- freeze_manifest_sha256: `10b9a42b50f68025379f6658b6733a4251e3a4ff95d78d8a7cca6579bd21b2d6`
- app_version: 0.1.0
- generated_at: 2026-10-01T05:32:27.030355+00:00
- run_duration_ms: 31264.1818
- holdout_intact: True
- holdout_detail: intact: 19 cases, sha256=9f9d1dbb04df5147..., frozen_at=2026-09-19T06:25:25.284526+00:00

## Scope

- metrics_scope: graded_rows_only
- graded_rows: 16
- ungraded_rows: 0
- ground_truth_resolution: {'absent': 4, 'resolved': 12}
- ungraded 行仅作诊断，不进入下方 Recall/MRR。ground_truth_mode=keyword_fallback 表示标签未能解析到当前知识库，该行结论不可信，需先修标注。

## Configuration

- embedding: bge / BAAI/bge-small-zh-v1.5
- embedding_dimension: 512
- experiment_mode: vector-only
- query_strategy: original
- adjacent_filter_strategy: current
- candidate_expansion: semantic-query-shadow
- supplemental_consumption: none
- supplemental_k: 1
- retrieval: top_k=6, candidate_k=20, min_score=0.013
- rrf_k: 60
- heuristic_weights: {'vector': 0.003, 'text': 0.004, 'lexical': 0.006}
- knowledge_base: AgentMentor BGE 验收知识库 (documents=7, active=7, ready=7, chunks=195, catalog_points=195)

## Metrics (graded rows only)

- total: 16
- Recall@1: 0.0833
- Recall@3: 0.0833
- Recall@6: 0.1667
- MRR: 0.1042
- Full answerability accuracy: 0.5
- Partial answerability accuracy: 0.0
- Evidence sufficient accuracy: 0.375
- Negative rejection accuracy: 0.0
- Full acceptance rate: 0.5
- Partial acceptance rate: 0.0
- Partial boundary detection rate: 0.0
- None rejection rate: 0.0
- Evidence macro accuracy: 0.0
- Evidence confusion matrix: {'full': {'full': 0, 'partial': 0, 'none': 0}, 'partial': {'full': 0, 'partial': 0, 'none': 0}, 'none': {'full': 0, 'partial': 0, 'none': 0}}
- Rejection by negative reason: {'false_premise': 0.0, 'in_domain_value_missing': 0.0}
- Retrieval latency P50/P95 ms: 70.2877 / 30209.9605
- Average candidate count: 6.0
- Candidate Recall@20: 0.5833
- Pre-filter Recall@6: 0.1667
- Post-filter Recall@6: 0.1667
- Primary@6 + supplemental@1: 0.1667
- Primary@6 + supplemental@3: 0.1667
- Primary@6 + supplemental@6: 0.1667
- Primary@6 + supplemental@20: 0.1667
- Average supplemental candidate count: 2.5833
- Supplemental trigger count/rate: 0 / 0.0
- Average consumed supplemental count: 0.0
- Gate promotions/demotions: 0 / 0
- Consumed relevant count/per trigger: 0 / 0.0
- Diversity filter drop rate: 0.3656
- Failure category counts: {'candidate_recall_miss': 5, 'false_acceptance': 4, 'per_document_filter_miss': 1, 'ranking_cutoff_miss': 4}

## Evidence Gate Failures

### trg-hn-001

- question: RRF 排名融合在生产环境每秒最多可以处理多少次查询？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 5
- diagnostic_keyword_coverage: {}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.6216660367449511

### trg-hn-002

- question: 面试 Checkpoint 默认会在数据库中保留多少天？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 6
- diagnostic_keyword_coverage: {}
- top_document: 第 7 课：工程化专题 + 面试实战
- top_score: 0.6729562483118849

### trg-hn-003

- question: 画像渐进更新公式中的系数经过了多少名用户的 A/B 实验？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 3
- diagnostic_keyword_coverage: {}
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.658571560936319

### trg-hn-004

- question: 引用白名单是否已经把事实错误率稳定降低到 1% 以下？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 3
- diagnostic_keyword_coverage: {}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.569367851652632

### trg-lp-001

- question: 两套搜索机制给出的数值单位无法互换时，系统怎样把它们汇成一个次序？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.5530330209116338

### trg-lp-002

- question: 浏览器意外关掉后，怎样接着完成上次还没结束的模拟面谈？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {}
- top_document: 第 4 课：可恢复模拟面试工作流
- top_score: 0.5943690538406372

### trg-lp-003

- question: 一次表现很好，为什么不能马上抹掉此前反复暴露的薄弱记录？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {}
- top_document: 第 5 课：可信评分与报告
- top_score: 0.5836640248498912

### trg-lp-004

- question: 负责二次核验的模型暂时失联时，为什么不能把初评分直接盖章？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.6169615387916565

### trg-hc-001

- question: 资料目录整体换了顺序以后，旧证据位置怎样避免全部失效？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.630397636604239

### trg-dn-002

- question: 防止同一份回答被重复处理依赖哪三层保护？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {}
- top_document: 第 7 课：工程化专题 + 面试实战
- top_score: 0.6189084833535102

## Failure Attribution

- `trg-hn-001`: false_acceptance (decision=accept, rank=None)
- `trg-hn-002`: false_acceptance (decision=accept, rank=None)
- `trg-hn-003`: false_acceptance (decision=accept, rank=None)
- `trg-hn-004`: false_acceptance (decision=accept, rank=None)
- `trg-lp-001`: candidate_recall_miss (decision=reject, rank=None)
- `trg-lp-002`: ranking_cutoff_miss (decision=reject, rank=None)
- `trg-lp-003`: ranking_cutoff_miss (decision=reject, rank=None)
- `trg-lp-004`: candidate_recall_miss (decision=reject, rank=None)
- `trg-hc-001`: candidate_recall_miss (decision=reject, rank=None)
- `trg-hc-002`: ranking_cutoff_miss (decision=accept, rank=None)
- `trg-hc-003`: per_document_filter_miss (decision=accept, rank=None)
- `trg-hc-004`: candidate_recall_miss (decision=accept, rank=None)
- `trg-dn-002`: ranking_cutoff_miss (decision=reject, rank=None)
- `trg-dn-003`: candidate_recall_miss (decision=accept, rank=None)

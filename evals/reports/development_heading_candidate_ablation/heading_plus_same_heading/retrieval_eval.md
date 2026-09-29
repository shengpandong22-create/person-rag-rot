# Retrieval Eval Report

## Reproducibility

- git_commit: `744ef3b43b9fad5dce280a3a485d68c69dc860ca` (dirty=True)
- git_branch: `codex/eval-foundation-rebuild`
- dataset: `evals\datasets\retrieval_development_v1.jsonl`
- dataset_sha256: `50c3d73b7bb67a1f5069d52a9c3d21bb1c8a3481d7ecb4250d7accb7a159d705`
- freeze_manifest_sha256: `None`
- app_version: 0.1.0
- generated_at: 2026-09-29T13:45:39.118844+00:00
- run_duration_ms: 131628.9284
- holdout_intact: True
- holdout_detail: intact: 19 cases, sha256=9f9d1dbb04df5147..., frozen_at=2026-09-19T06:25:25.284526+00:00

## Scope

- metrics_scope: graded_rows_only
- graded_rows: 60
- ungraded_rows: 0
- ground_truth_resolution: {'absent': 35, 'resolved': 25}
- ungraded 行仅作诊断，不进入下方 Recall/MRR。ground_truth_mode=keyword_fallback 表示标签未能解析到当前知识库，该行结论不可信，需先修标注。

## Configuration

- embedding: bge / BAAI/bge-small-zh-v1.5
- embedding_dimension: 512
- experiment_mode: vector-only
- query_strategy: original
- adjacent_filter_strategy: same-heading
- candidate_expansion: heading-lexical
- retrieval: top_k=6, candidate_k=20, min_score=0.013
- rrf_k: 60
- heuristic_weights: {'vector': 0.003, 'text': 0.004, 'lexical': 0.006}
- knowledge_base: AgentMentor BGE 验收知识库 (documents=7, active=7, ready=7, chunks=195, catalog_points=195)

## Metrics (graded rows only)

- total: 60
- Recall@1: 0.4
- Recall@3: 0.6
- Recall@6: 0.76
- MRR: 0.51
- Full answerability accuracy: 0.9333
- Partial answerability accuracy: 1.0
- Evidence sufficient accuracy: 0.5333
- Negative rejection accuracy: 0.2286
- Full acceptance rate: 0.9333
- Partial acceptance rate: 1.0
- Partial boundary detection rate: 0.0
- None rejection rate: 0.2286
- Evidence macro accuracy: 0.3873
- Evidence confusion matrix: {'full': {'full': 14, 'partial': 0, 'none': 1}, 'partial': {'full': 10, 'partial': 0, 'none': 0}, 'none': {'full': 27, 'partial': 0, 'none': 8}}
- Rejection by negative reason: {'false_premise': 0.0, 'in_domain_no_conclusion': 0.4, 'in_domain_value_missing': 0.2857, 'out_of_range_implementation': 0.4, 'out_of_scope': 0.2, 'version_not_released': 0.2}
- Retrieval latency P50/P95 ms: 72.6885 / 179.6127
- Average candidate count: 6.0
- Candidate Recall@20: 0.88
- Pre-filter Recall@6: 0.72
- Post-filter Recall@6: 0.76
- Diversity filter drop rate: 0.4117
- Failure category counts: {'candidate_recall_miss': 3, 'correct_rejection': 8, 'evidence_gate_rejection': 1, 'false_acceptance': 27, 'partial_answer_boundary': 9, 'per_document_filter_miss': 3}

## Evidence Gate Failures

### dev-neg-001

- question: 系统当前配置的 HNSW ef_search 精确值是多少？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.03009207275993712

### dev-neg-002

- question: 一次最多允许多少名用户并发进行模拟面试？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 1 课：项目全景与架构地图
- top_score: 0.01639344262295082

### dev-neg-004

- question: 评分置信度 0.70 是通过多少条人工样本校准出来的？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 5 课：可信评分与报告
- top_score: 0.03128054740957967

### dev-neg-005

- question: 为什么 AgentMentor 选择 FastAPI 而不是 Django？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {}
- top_document: 第 1 课：项目全景与架构地图
- top_score: 0.03047794966520434

### dev-neg-008

- question: Beta 分布是否比当前渐进掌握度公式更准确？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {}
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.031099324975891997

### dev-neg-009

- question: AgentMentor V3 会在哪一天发布？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 1 课：项目全景与架构地图
- top_score: 0.01639344262295082

### dev-neg-010

- question: 下一版会默认切换到哪个 CrossEncoder 模型？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {}
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.02938045560996381

### dev-neg-011

- question: 未来迁移 LangGraph 时会采用哪个具体版本？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 1 课：项目全景与架构地图
- top_score: 0.031054405392392875

### dev-neg-013

- question: 当前 Redis 缓存的失效策略是什么？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 4 课：可恢复模拟面试工作流
- top_score: 0.03055037313432836

### dev-neg-016

- question: 当前多租户 RBAC 如何隔离不同公司的知识库？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.02946912242686891

### dev-neg-017

- question: 既然当前工作流运行在 LangGraph 上，StateGraph 节点失败后怎样自动补偿？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 5
- diagnostic_keyword_coverage: {}
- top_document: 第 7 课：工程化专题 + 面试实战
- top_score: 0.03149801587301587

### dev-neg-018

- question: Elasticsearch 已经承担全文检索后，PostgreSQL 为什么还保留 tsvector？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.028814262023217248

### dev-neg-019

- question: LLM 直接给出的 total_score 为什么还要原样写入数据库？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 5 课：可信评分与报告
- top_score: 0.01639344262295082

### dev-neg-020

- question: 一次高分已经把 mastery 设置成 100%，之后为什么还要复习？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {}
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.03177805800756621

### dev-neg-022

- question: JVM ZGC 的染色指针如何与 RRF 融合？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 5
- diagnostic_keyword_coverage: {}
- top_document: 第 3 课：混合检索与可信 RAG 回答
- top_score: 0.031746031746031744

### dev-neg-023

- question: CUDA kernel 的 shared memory 如何优化本地 BGE？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.03177805800756621

### dev-neg-024

- question: 量子退火如何改进面试题调度？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.031099324975891997

### dev-neg-025

- question: 资料一处说默认 BGE、一处展示 DevelopmentEmbeddingGateway，所以线上究竟固定使用哪一个且永不降级？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {}
- top_document: 第 1 课：项目全景与架构地图
- top_score: 0.01639344262295082

### dev-neg-026

- question: 资料既说 checkpoint 支持恢复又说它不能自动续跑，所以服务重启后会从哪一行 Python 代码继续？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 5
- diagnostic_keyword_coverage: {}
- top_document: 第 4 课：可恢复模拟面试工作流
- top_score: 0.03200204813108039

### dev-neg-027

- question: Reviewer 默认始终可用但未来又可能不可用，生产环境现在的独立 Reviewer SLA 是多少？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 4
- diagnostic_keyword_coverage: {}
- top_document: 第 5 课：可信评分与报告
- top_score: 0.03278688524590164

### dev-neg-028

- question: 资料既强调模块化单体又讨论迁移工作流框架，当前到底部署了多少个微服务？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 1 课：项目全景与架构地图
- top_score: 0.0315136476426799

### dev-pos-010

- question: 为什么事务边界比单纯保证调用顺序更重要？
- answerability: full
- evidence_sufficient: False
- supported_chunk_count: 0
- diagnostic_keyword_coverage: {}
- top_document: 第 1 课：项目全景与架构地图
- top_score: 0.03225806451612903

### dev-neg-034

- question: 独立 Reviewer 应该使用同一模型还是异构模型更好？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 3
- diagnostic_keyword_coverage: {}
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.029957522915269395

### dev-neg-035

- question: AgentMentor 下一版本会不会删除 development embedding fallback？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.029551337359792925

### dev-neg-036

- question: 当前 Celery worker 的重试退避参数是多少？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 2
- diagnostic_keyword_coverage: {}
- top_document: 第 4 课：可恢复模拟面试工作流
- top_score: 0.01639344262295082

### dev-neg-037

- question: 既然当前使用 Pinecone，pgvector 数据如何实时双写？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.030117753623188408

### dev-neg-038

- question: Rust borrow checker 怎样保证画像更新线程安全？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 3
- diagnostic_keyword_coverage: {}
- top_document: 第 6 课：两层画像与复习闭环
- top_score: 0.031099324975891997

### dev-neg-039

- question: 资料说新文档进入目录但又不改变已有画像，因此上传后用户掌握度究竟应该立即增加多少？
- answerability: none
- evidence_sufficient: True
- supported_chunk_count: 1
- diagnostic_keyword_coverage: {}
- top_document: 第 2 课：知识入库链路——文档如何变成可检索证据
- top_score: 0.0315136476426799

## Failure Attribution

- `dev-neg-001`: false_acceptance (decision=accept, rank=None)
- `dev-neg-002`: false_acceptance (decision=accept, rank=None)
- `dev-neg-003`: correct_rejection (decision=reject, rank=None)
- `dev-neg-004`: false_acceptance (decision=accept, rank=None)
- `dev-neg-005`: false_acceptance (decision=accept, rank=None)
- `dev-neg-006`: correct_rejection (decision=reject, rank=None)
- `dev-neg-007`: correct_rejection (decision=reject, rank=None)
- `dev-neg-008`: false_acceptance (decision=accept, rank=None)
- `dev-neg-009`: false_acceptance (decision=accept, rank=None)
- `dev-neg-010`: false_acceptance (decision=accept, rank=None)
- `dev-neg-011`: false_acceptance (decision=accept, rank=None)
- `dev-neg-012`: correct_rejection (decision=reject, rank=None)
- `dev-neg-013`: false_acceptance (decision=accept, rank=None)
- `dev-neg-014`: correct_rejection (decision=reject, rank=None)
- `dev-neg-015`: correct_rejection (decision=reject, rank=None)
- `dev-neg-016`: false_acceptance (decision=accept, rank=None)
- `dev-neg-017`: false_acceptance (decision=accept, rank=None)
- `dev-neg-018`: false_acceptance (decision=accept, rank=None)
- `dev-neg-019`: false_acceptance (decision=accept, rank=None)
- `dev-neg-020`: false_acceptance (decision=accept, rank=None)
- `dev-neg-021`: correct_rejection (decision=reject, rank=None)
- `dev-neg-022`: false_acceptance (decision=accept, rank=None)
- `dev-neg-023`: false_acceptance (decision=accept, rank=None)
- `dev-neg-024`: false_acceptance (decision=accept, rank=None)
- `dev-neg-025`: false_acceptance (decision=accept, rank=None)
- `dev-neg-026`: false_acceptance (decision=accept, rank=None)
- `dev-neg-027`: false_acceptance (decision=accept, rank=None)
- `dev-neg-028`: false_acceptance (decision=accept, rank=None)
- `dev-neg-029`: partial_answer_boundary (decision=accept, rank=1)
- `dev-neg-030`: partial_answer_boundary (decision=accept, rank=6)
- `dev-neg-031`: candidate_recall_miss (decision=accept, rank=None)
- `dev-neg-032`: partial_answer_boundary (decision=accept, rank=3)
- `dev-pos-003`: per_document_filter_miss (decision=accept, rank=None)
- `dev-pos-006`: candidate_recall_miss (decision=accept, rank=None)
- `dev-pos-008`: candidate_recall_miss (decision=accept, rank=None)
- `dev-pos-010`: evidence_gate_rejection (decision=reject, rank=3)
- `dev-neg-033`: correct_rejection (decision=reject, rank=None)
- `dev-neg-034`: false_acceptance (decision=accept, rank=None)
- `dev-neg-035`: false_acceptance (decision=accept, rank=None)
- `dev-neg-036`: false_acceptance (decision=accept, rank=None)
- `dev-neg-037`: false_acceptance (decision=accept, rank=None)
- `dev-neg-038`: false_acceptance (decision=accept, rank=None)
- `dev-neg-039`: false_acceptance (decision=accept, rank=None)
- `dev-pt-005`: partial_answer_boundary (decision=accept, rank=1)
- `dev-pt-006`: partial_answer_boundary (decision=accept, rank=1)
- `dev-pt-007`: partial_answer_boundary (decision=accept, rank=1)
- `dev-pt-008`: partial_answer_boundary (decision=accept, rank=1)
- `dev-pt-009`: partial_answer_boundary (decision=accept, rank=3)
- `dev-pt-010`: partial_answer_boundary (decision=accept, rank=4)
- `dev-pos-012`: per_document_filter_miss (decision=accept, rank=None)
- `dev-pos-013`: per_document_filter_miss (decision=accept, rank=None)

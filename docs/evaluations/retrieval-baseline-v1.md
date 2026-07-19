# Retrieval Baseline V1

Status: scaffolded for Phase 2.

This baseline uses `evals/datasets/retrieval_v1.jsonl` as the first retrieval question set:

- 30 retrieval questions.
- 4 intentionally unanswerable questions.
- Metrics to report after executable evaluation is wired to a seeded knowledge base: Recall@5, MRR, NDCG, and refusal behavior for unanswerable questions.

Current implementation note:

- Hybrid retrieval combines pgvector semantic search and PostgreSQL full-text search through RRF.
- The local development setup still uses deterministic embeddings, so the first numeric baseline is useful for regression testing, not for claiming production retrieval quality.

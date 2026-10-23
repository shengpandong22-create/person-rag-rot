# Coverage Catalog Acceptance Contract V1

## Scope

This contract evaluates one bounded production behavior: a user-selected coverage gap may advance only
through a persisted citation to that catalog point's own source chunk. It does not evaluate RAG recall,
answer correctness, profile-score accuracy, or automatic bulk reindexing.

## Frozen fixture and protocol

- Fixture: `evals/fixtures/coverage-loop-acceptance-v1.md`
- Fixture SHA-256: recorded by `scripts/run_coverage_loop_acceptance.py` in the raw result.
- Target: catalog point `RRF 公式` in a fresh, isolated knowledge base created by the runner.
- Runtime: record `/health/runtime`; no test-mode fake LLM is acceptable for this acceptance.
- Minimum runs: 3 independent interview sessions with `coverage_catalog_point_id` fixed to the target.
- Runner: `scripts/run_coverage_loop_acceptance.py --runs 3 --output <result.json>`.

## Hard gates

1. Each generated question persists at least one `question_references.chunk_id` that equals one of the
   selected point's `knowledge_catalog_sources.chunk_id` values.
2. Each question's coverage mapping is derived by `map_question_coverage`; no forced target mapping helper
   exists.
3. A target ID from another knowledge base, or one without a source chunk, is rejected at creation time.
4. Structural headings such as `一个具体例子` do not create new catalog points on ingestion.
5. The runner must retain raw question text, citation IDs, model/runtime metadata, fixture hash, and every
   run result. Any failed run fails the candidate; it is not rerun as a parameter-tuning exercise.

## Existing data policy

Existing catalog links and historic coverage rows are retained. Coverage statistics count only rows with
source-provenance; no automatic user knowledge-base reindex is authorized by this contract.

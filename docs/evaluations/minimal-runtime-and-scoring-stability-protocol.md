# Minimal Runtime and Scoring Stability Protocol

## Purpose

This protocol adds two bounded observations to the interview evidence set:

1. sequential single-request runtime latency for retrieval and `/ask`;
2. five repeated evaluations of one fixed answer with a fixed real-model configuration.

It does not reopen retrieval ablations, run HNSW tuning, claim QPS capacity, or estimate human scoring agreement.

## Runtime baseline contract

- Use one dedicated benchmark knowledge base only. `/ask` persists chat records.
- `docker-compose.runtime-benchmark.yml` supplies an isolated benchmark database and APIs on
  `18000` / `18001`; it neither uses nor maps the normal `5432` database port.
- Start two isolated AgentMentor API instances that point to the same benchmark data and use the same embedding provider/model/dimension:
  - fallback instance: no LLM credentials, therefore `/health/runtime` reports `llm_enabled: false`;
  - real-model instance: configured LLM credentials, therefore `/health/runtime` reports `llm_enabled: true`.
- Fix `top_k=6`, `candidate_k=20`, and use `evals/datasets/runtime_baseline_v1.jsonl`.
- Run sequentially, with four measured repetitions per five questions and one warmup. This gives 20 samples per mode/phase; it is not a concurrency test.
- Record endpoint P50/P95, retrieval P50/P95, failure rate, and the end-to-end breakdown by
  `generation_mode`. The runner fails fast if the two runtime snapshots disagree on embedding
  provider/model/dimension. A mixed endpoint number must never be presented as model-generation
  latency; only the `generation_mode=llm` subgroup represents an external model call.

Create the isolated stack, migrate it once, then start both APIs:

```powershell
docker compose -p agentmentor-runtime-benchmark -f docker-compose.yml -f docker-compose.runtime-benchmark.yml up -d db
docker compose -p agentmentor-runtime-benchmark -f docker-compose.yml -f docker-compose.runtime-benchmark.yml run --rm api-fallback alembic upgrade head
docker compose -p agentmentor-runtime-benchmark -f docker-compose.yml -f docker-compose.runtime-benchmark.yml up -d api-fallback api-llm
python scripts/setup_runtime_baseline_kb.py --base-url http://localhost:18000
```

Then use the returned `knowledge_base_id`:

```powershell
python scripts/run_runtime_baseline.py `
  --fallback-base-url http://localhost:18000 `
  --llm-base-url http://localhost:18001 `
  --knowledge-base-id <benchmark-kb-uuid> `
  --output-dir evals/reports/runtime_baseline_v1 `
  --allow-persistent-chat-writes
```

The report must be described as a machine- and configuration-specific sequential observation. It cannot be presented as a load test, throughput result, or production SLO.

## Scoring stability contract

- Fixed dataset/case: `evals/datasets/evaluation_discrimination_v1.jsonl`, `disc-evaluation-high`.
- Fixed configured real model; the runner captures its model name.
- Exactly five sequential direct evaluations; no interview rows, user answers, profiles, or review tasks are written.
- Reviewer is deliberately disabled so the observation isolates the primary evaluator rather than the deterministic review branch.
- Report total/dimension ranges, population standard deviation, score-shape stability, and review-route stability.

```powershell
python scripts/run_scoring_stability.py `
  --output-dir evals/reports/scoring_stability_v1
```

This is a small-sample repeatability observation only. It does not measure accuracy against human labels, reviewer override rate, or inter-rater reliability.

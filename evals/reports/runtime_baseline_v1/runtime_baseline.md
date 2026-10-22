# Minimal Runtime Baseline

## Scope

This is a sequential single-request observation, not a concurrency load test or QPS claim.
The `/ask` endpoint persists chat records, so this run is restricted to a dedicated benchmark knowledge base.

## Reproducibility

- generated_at: `2026-10-22T13:32:00.072884+00:00`
- git_commit: `55644b147ff9d5c8f8f09552737c522b815e56d9`
- git_branch: `codex/eval-foundation-rebuild`
- dataset: `evals\datasets\runtime_baseline_v1.jsonl`
- dataset_sha256: `e0ac52743a893fff3f7d971751bc0128f6088cc40ae7888d700752edfcd5e0a7`
- knowledge_base_id: `58908e5f-7bb2-4973-9f2b-8ea759ac7e6a`
- repetitions: `4`
- warmups: `1`
- runtime_modes: `{'fallback': {'status': 'ok', 'app_version': '0.1.0', 'started_at': '2026-10-22T13:26:34.119987+00:00', 'llm_enabled': False, 'llm_model': None, 'embedding_provider': 'bge', 'embedding_model': 'BAAI/bge-small-zh-v1.5', 'embedding_dimension': 512}, 'llm': {'status': 'ok', 'app_version': '0.1.0', 'started_at': '2026-10-22T13:26:34.122255+00:00', 'llm_enabled': True, 'llm_model': 'deepseek-chat', 'embedding_provider': 'bge', 'embedding_model': 'BAAI/bge-small-zh-v1.5', 'embedding_dimension': 512}}`

## Results

| mode / phase | samples | failures | failure rate | P50 ms | P95 ms |
|---|---:|---:|---:|---:|---:|
| fallback:end_to_end | 20 | 0 | 0.00% | 72.08 | 129.749 |
| fallback:retrieval | 20 | 0 | 0.00% | 76.042 | 140.634 |
| llm:end_to_end | 20 | 0 | 0.00% | 1052.281 | 1493.324 |
| llm:retrieval | 20 | 0 | 0.00% | 47.806 | 65.611 |

## End-to-end outcome breakdown

This table separates Evidence Gate responses from actual LLM generation. Only the `llm` generation row represents an external model call.

| mode / generation mode | samples | failures | failure rate | P50 ms | P95 ms |
|---|---:|---:|---:|---:|---:|
| fallback:end_to_end:deterministic | 20 | 0 | 0.00% | 72.08 | 129.749 |
| llm:end_to_end:llm | 20 | 0 | 0.00% | 1052.281 | 1493.324 |

## Interpretation boundary

P50/P95 describe only these sequential samples on the recorded machine and runtime. They do not establish throughput, concurrent capacity, or a production SLO.

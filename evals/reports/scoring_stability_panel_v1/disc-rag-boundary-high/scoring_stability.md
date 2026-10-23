# Scoring Stability Observation

## Scope and boundary

The same fixed answer was evaluated five times with a fixed configured model. The reviewer step was disabled to isolate the primary evaluator.
This is a small-sample repeatability observation, not a human adjudication study, accuracy result, or reviewer override rate.

## Reproducibility

- dataset: `evals\datasets\evaluation_discrimination_v1.jsonl`
- dataset_sha256: `91361bd24fd42baafec2a338f4d8fe53f6b753f84f5916d9b6c6ef0d6ee06571`
- case_id: `disc-rag-boundary-high`
- llm_model: `deepseek-chat`
- git_commit: `1a9c2359bed09a96f2501f0ce80f094e570b032d`

## Result

- total-score range: `15–15`
- total-score population standard deviation: `0.0`
- exact score shape stable: `True`
- review routing stable: `True`

| run | total | correctness | completeness | reasoning | communication | confidence | elapsed ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 15 | 4 | 3 | 4 | 4 | 0.8 | 2779.039 |
| 2 | 15 | 4 | 3 | 4 | 4 | 0.8 | 2180.367 |
| 3 | 15 | 4 | 3 | 4 | 4 | 0.8 | 2833.054 |
| 4 | 15 | 4 | 3 | 4 | 4 | 0.8 | 2332.38 |
| 5 | 15 | 4 | 3 | 4 | 4 | 0.75 | 2778.433 |

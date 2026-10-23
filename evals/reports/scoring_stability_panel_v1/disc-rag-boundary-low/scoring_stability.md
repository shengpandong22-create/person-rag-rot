# Scoring Stability Observation

## Scope and boundary

The same fixed answer was evaluated five times with a fixed configured model. The reviewer step was disabled to isolate the primary evaluator.
This is a small-sample repeatability observation, not a human adjudication study, accuracy result, or reviewer override rate.

## Reproducibility

- dataset: `evals\datasets\evaluation_discrimination_v1.jsonl`
- dataset_sha256: `91361bd24fd42baafec2a338f4d8fe53f6b753f84f5916d9b6c6ef0d6ee06571`
- case_id: `disc-rag-boundary-low`
- llm_model: `deepseek-chat`
- git_commit: `1a9c2359bed09a96f2501f0ce80f094e570b032d`

## Result

- total-score range: `4–5`
- total-score population standard deviation: `0.4`
- exact score shape stable: `False`
- review routing stable: `True`

| run | total | correctness | completeness | reasoning | communication | confidence | elapsed ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 1 | 1 | 1 | 2 | 0.9 | 2759.523 |
| 2 | 5 | 1 | 1 | 1 | 2 | 0.9 | 3135.145 |
| 3 | 5 | 1 | 1 | 1 | 2 | 0.9 | 2424.326 |
| 4 | 4 | 1 | 1 | 0 | 2 | 0.9 | 2302.357 |
| 5 | 5 | 1 | 1 | 1 | 2 | 0.9 | 2731.109 |

# Scoring Stability Observation

## Scope and boundary

The same fixed answer was evaluated five times with a fixed configured model. The reviewer step was disabled to isolate the primary evaluator.
This is a small-sample repeatability observation, not a human adjudication study, accuracy result, or reviewer override rate.

## Reproducibility

- dataset: `evals\datasets\evaluation_discrimination_v1.jsonl`
- dataset_sha256: `91361bd24fd42baafec2a338f4d8fe53f6b753f84f5916d9b6c6ef0d6ee06571`
- case_id: `disc-evaluation-high`
- llm_model: `deepseek-chat`
- git_commit: `55644b147ff9d5c8f8f09552737c522b815e56d9`

## Result

- total-score range: `19–20`
- total-score population standard deviation: `0.4`
- exact score shape stable: `False`
- review routing stable: `True`

| run | total | correctness | completeness | reasoning | communication | confidence | elapsed ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 20 | 5 | 5 | 5 | 5 | 0.9 | 1786.363 |
| 2 | 19 | 5 | 4 | 5 | 5 | 0.9 | 2280.0 |
| 3 | 19 | 5 | 4 | 5 | 5 | 0.9 | 2610.326 |
| 4 | 19 | 5 | 4 | 5 | 5 | 0.9 | 2107.682 |
| 5 | 19 | 5 | 4 | 5 | 5 | 0.9 | 2306.356 |

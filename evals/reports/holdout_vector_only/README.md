# Holdout Final Acceptance — vector-only

This is the single authorized holdout run for the candidate selected on
validation. No algorithm or parameter was changed after observing this result.

## Result

| Metric | Value |
|---|---:|
| Recall@1 | 0.3333 |
| Recall@3 | 0.5556 |
| Recall@6 | 0.5556 |
| MRR | 0.4259 |
| Full answerability accuracy | 0.8889 |
| Partial answerability accuracy | N/A (no partial cases) |
| Negative rejection accuracy | 0.3000 |
| Retrieval latency P50 | 50.0478 ms |
| Retrieval latency P95 | 34128.8320 ms |
| Average returned candidates | 6.0000 |

The P95 includes the one-time local embedding-model cold start. The run was not
repeated to remove that cost because the holdout protocol permits only one run
per candidate.

## Negative rejection by reason

| Reason | Rejection rate |
|---|---:|
| false_premise | 0.3333 |
| in_domain_no_conclusion | 0.0000 |
| in_domain_value_missing | 0.2500 |
| out_of_range_implementation | 0.0000 |
| version_not_released | 1.0000 |

## Outcome

The candidate does not demonstrate a trustworthy holdout baseline. Ranking
recall is moderate, but seven of ten negative cases were falsely accepted.
There were also four positive retrieval misses and one evidence-gate rejection
of a retrieved positive. These findings are acceptance evidence only and were
not used to tune the implementation.

Detailed per-case evidence, ranks, scores, decisions, and failure categories
are preserved in `retrieval_eval.json` and `retrieval_eval.md`.

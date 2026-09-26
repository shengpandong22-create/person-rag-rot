# Validation Retrieval Ablation Decision

## Decision

Recommend `vector-only` as the single holdout candidate. It ties RRF and
RRF+heuristic on Recall@3/6, while producing the best Recall@1 and MRR and a
substantially lower P50/P95 latency than either hybrid mode.

Holdout has not been run.

## Comparable metrics

| mode | Recall@1 | Recall@3 | Recall@6 | MRR | full acc. | partial acc. | negative rejection | P50 ms | P95 ms | avg. candidates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| vector-only | 0.3529 | 0.5294 | 0.7059 | 0.4853 | 1.0000 | 1.0000 | 1.0000 | 39.1750 | 58.5544 | 6.0000 |
| text-only | 0.1765 | 0.3529 | 0.4118 | 0.2667 | 1.0000 | 1.0000 | 1.0000 | 30.8845 | 50.1426 | 6.0000 |
| RRF | 0.2941 | 0.5294 | 0.7059 | 0.4461 | 1.0000 | 1.0000 | 1.0000 | 82.2099 | 355.7632 | 6.0000 |
| RRF + heuristic | 0.1765 | 0.5294 | 0.7059 | 0.3647 | 1.0000 | 1.0000 | 1.0000 | 76.2197 | 95.7942 | 6.0000 |

All four modes rejected every validation negative in each represented
`negative_reason` group.

## Failure attribution

| mode | retrieval_miss | partial_answer_boundary | correct_rejection |
|---|---:|---:|---:|
| vector-only | 5 | 2 | 5 |
| text-only | 10 | 1 | 5 |
| RRF | 5 | 1 | 5 |
| RRF + heuristic | 5 | 1 | 5 |

The per-case JSON and Markdown reports under each mode directory contain the
retrieved chunk IDs, logical document names, heading paths, source ranks and
scores, RRF and heuristic scores, evidence decisions, and failure categories.

## Known limitations

- Validation contains 17 positive and 5 negative cases, so answerability and
  negative-rejection estimates have wide uncertainty despite perfect observed
  accuracy.
- Latency is a local single-process measurement and includes database and local
  embedding inference; it is useful for same-run comparison, not a production
  SLO.
- Average candidate count is the number returned after production diversity
  filtering and top-k truncation, not the raw per-source candidate pool.
- The knowledge base was reindexed with the current parser and unchanged
  chunk/embedding configuration before the final run because its stored chunks
  predated fenced-code heading handling. All 17 positive labels resolved after
  reindexing.

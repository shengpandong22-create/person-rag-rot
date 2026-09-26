# Validation Retrieval Stage Diagnostics

This report adds stage-level attribution to the frozen validation set without
changing retrieval ranking, filtering, Top-K, or Evidence Gate behavior.
Holdout was not run.

## Behavioral equivalence

The vector-only baseline is unchanged:

| Metric | Before | With diagnostics |
|---|---:|---:|
| Recall@1 | 0.3529 | 0.3529 |
| Recall@3 | 0.5294 | 0.5294 |
| Recall@6 | 0.7059 | 0.7059 |
| MRR | 0.4853 | 0.4853 |

## Stage metrics

| Metric | Value |
|---|---:|
| Candidate Recall@20 | 0.8824 |
| Pre-filter Recall@6 | 0.8235 |
| Post-filter Recall@6 | 0.7059 |
| Diversity filter drop rate | 0.3432 |

## Positive failure attribution

| Category | Count |
|---|---:|
| candidate_recall_miss | 2 |
| per_document_filter_miss | 3 |
| ranking_cutoff_miss | 0 |
| adjacent_filter_miss | 0 |

The selected vector-only baseline does not currently show a material Top-K
ranking-cutoff problem on validation. Of five positive Top-6 misses, two never
entered the 20-candidate pool and three were removed by the existing
per-document limit. This is diagnostic evidence only; no retrieval parameter
or algorithm was changed in this phase.

Some relevant chunks were filtered in otherwise successful cases because a
different chunk matching the same human source label survived. A filter miss
is therefore assigned only when no relevant chunk remains after that stage.

Detailed per-case raw candidate IDs, post-filter IDs, filter reasons, ranks,
scores, and ground-truth matches are stored in the vector-only JSON report.

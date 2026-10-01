# Typed Demand-Binding V2 Development Result

## Configuration

- Frozen dataset SHA-256: `c0f501397764d9c42d006d7eec6ba6dbcd36248fd01219f1072b2a0e3dcff3df`
- Retrieval: vector-only, top_k=6, candidate_k=20
- Candidate expansion: heading-shadow, consumption=none
- Gate candidate: `typed-local-v2`
- No regression, validation, acceptance, or holdout run was performed.

`typed-local-v2` adds unit-alias normalization (`回/轮 -> 次`, `自然日 -> 天`, decimal
fractions for `成`), explicit range recognition, same-chunk bounded two-segment windows, and matched
chunk provenance. It does not alter the production Gate.

## Result

| metric | production reference | numeric-local-v1 | typed-local-v2 |
|---|---:|---:|---:|
| Evidence accuracy | 0.8667 | 1.0000 | 0.9333 |
| Full acceptance | 1.0000 | 1.0000 | 0.9000 |
| Negative rejection | 0.6000 | 1.0000 | 1.0000 |
| Labeled evidence acceptance | 0.6000 | 0.6000 | 0.6000 |
| Labeled evidence binding success | not available | not available | 0.5000 |

The new formal binding metric requires the accepted binding to name a chunk resolved from human
`relevant_sources`. Five of ten positive rows meet that condition.

## Failure audit

- Four positives (`db-ex-002`, `db-un-002`, `db-ra-002`, `db-ta-002`) have no labeled evidence in
  candidate@20. A Gate-only change cannot bind evidence that retrieval never supplied.
- `db-cr-002` retrieves its labeled source but binds the two requested values to another retrieved
  chunk. This is a provenance failure that answerability accuracy alone would hide.
- The typed range rule correctly rejects the unsupported latency range, and unit aliases are now
  represented explicitly, but those improvements do not compensate for the remaining retrieval and
  cross-span provenance failures.

## Decision

`typed-local-v2` is **not qualified for regression**. The formal qualification metric successfully
prevents a misleading pass based on 93.33% answerability accuracy. Further Gate tuning on this same
fixture should stop. The next safe step is to separate the four candidate-recall misses from the one
cross-span provenance error, then design a new candidate without changing this frozen dataset.

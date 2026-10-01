# Demand-Binding Retrieval/Provenance Split Diagnosis

## Gate line: cross-span provenance only

`typed-local-v2` now recognizes the implicit two-value request in `db-cr-002`. Both values must
appear in one bounded evidence window from one chunk; values found in separate chunks cannot be
combined. English code identifiers such as `learning_rate` are normalized only for predicate
matching.

Result on the unchanged frozen fixture:

| metric | before provenance fix | after provenance fix |
|---|---:|---:|
| Negative rejection | 1.0000 | 1.0000 |
| Full acceptance | 0.9000 | 0.9000 |
| Labeled evidence acceptance | 0.6000 | 0.6000 |
| Labeled evidence binding success | 0.5000 | 0.6000 |

`db-cr-002` now binds only to its resolved human-labeled chunk
`fd64b352-84d4-478e-8281-3f4b65e6c923`. The remaining gap is not attributed to the Gate.

## Retrieval line: four missing vector candidates

The four rows absent from vector candidate@20 were diagnosed independently with candidate_k=50 and
the Gate disabled. No RRF weight or production retrieval setting was changed.

| case | vector raw@20 | heading shadow@20 | vector raw@50 | post-filter@50 | attribution |
|---|---:|---:|---:|---:|---|
| `db-ex-002` | miss | 1 | 30 | miss | per-document limit |
| `db-un-002` | miss | 7 | 21 | 6 | per-document limit before final evidence position |
| `db-ra-002` | miss | 1 | 36 | miss | per-document limit |
| `db-ta-002` | miss | 2 | 23 | miss | per-document limit |

Increasing vector candidate depth does not improve Recall@6: it merely changes the attribution from
candidate miss to per-document filtering. The already-monotonic heading shadow finds all four at
ranks 1, 7, 1, and 2 without changing the primary Top-6. This is a retrieval-consumption problem,
not a reason to weaken demand binding or tune RRF.

## Decision

- Gate provenance repair is successful and remains eval-only.
- `typed-local-v2` is still not qualified for regression because formal binding success is 0.6000
  and full acceptance is 0.9000.
- candidate_k=50 is rejected as a retrieval candidate.
- Any next retrieval experiment should compare predeclared monotonic heading-shadow consumption
  policies on Development, with a maximum supplemental budget that can cover rank 7. It must remain
  separate from Gate changes.
- Regression, validation, acceptance, and holdout were not run.

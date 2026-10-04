# Relation-Value V3 Independent Acceptance Decision

## Decision

The frozen `relation-value-binding-v3` candidate failed its single completed independent
acceptance run and is **not accepted for production integration design**. The run is final for this
candidate and acceptance set. No rerun or acceptance-driven tuning is permitted.

The result does not indicate an infrastructure or evaluator failure: all 36 rows and 43 demands
were evaluated with zero unresolved labels and zero case errors. Candidate, acceptance, and
execution freezes remained intact before and after the run, report integrity passed, and production
isolation passed.

## Formal results

| Metric | Observed | Gate | Result |
| --- | ---: | ---: | --- |
| Demand accuracy | 0.3256 | >= 0.9000 | fail |
| Positive demand recall | 0.0645 | >= 0.8710 | fail |
| Positive all-demands row accuracy | 0.0833 | >= 0.8333 | fail |
| Negative demand rejection | 1.0000 | = 1.0000 | pass |
| Negative row rejection | 1.0000 | = 1.0000 | pass |
| Binding precision | 0.2222 | >= 0.9000 | fail |
| Paired discrimination | 0.0909 | >= 0.9091 | fail |
| Candidate P95 | 0.2291 ms | <= 50 ms | pass |

All six hard-negative categories achieved 2/2 rejection. Binding volume, evaluated counts, latency,
freeze integrity, report integrity, and production isolation also passed.

## Failure attribution

- Only 2 of 31 positive demands received a fully correct binding: `rva3-001/d1` and
  `rva3-006/d1`.
- Twenty-two positive demands produced no binding. This is the dominant failure and shows that the
  candidate's typed span, term-coverage, unit, or semantic filters are too restrictive for the
  independently labeled evidence forms.
- Seven positive demands emitted a binding that failed the complete human contract. Examples
  include normalizing a derived result as `exact`, retaining intermediate/distractor values instead
  of the accepted output, and binding a shared identifier rather than the requested version value.
- Twenty-two of 24 positive rows failed; 12 of 12 negative rows passed. The candidate is therefore
  conservative but not useful enough: it avoids false acceptance mainly by declining nearly all
  valid bindings.

This acceptance result isolates relation/value binding over frozen labeled evidence. It does not
measure retrieval recall or end-to-end answer quality, so the failure must not be attributed to
candidate retrieval.

## Immutable artifacts

| Artifact | SHA-256 |
| --- | --- |
| Attempt ledger | `b9bc8e380f64b6fcfe5a5aee056e61c835d05a780f3d9a8cb3ae78b4e2aa55d6` |
| Raw report | `bc02900ab8557d1c179b1e1be51d1c65c31865d516ec192a20d63d4c66a58e2e` |
| Qualification | `8a2527979c21a22a508077588e4758d4c417d5c2daadbbf486c6200f6d7b408f` |
| Generated summary | `0fa19ab02ebf1ecf7a41b445bef050b3e01a9aa8f5841d2272883a590cfcefb7` |

## Next-step boundary

V3 remains frozen and eval-only. A successor must use a new candidate identity and return to
non-blind Development. It may use this result only for high-level failure taxonomy; it must not be
tuned case-by-case against this acceptance set. Any future formal acceptance requires a newly
constructed, independently reviewed, and separately frozen dataset.

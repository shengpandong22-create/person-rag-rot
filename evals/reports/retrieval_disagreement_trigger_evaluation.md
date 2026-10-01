# Retrieval-Disagreement Trigger Evaluation

## Candidate

The eval-only `retrieval-disagreement@7` trigger consumes heading-shadow candidates only when:

1. the best supplemental heading score is at least 2; and
2. the vector Top-1 minus Top-2 score gap is at most 0.04.

The rule is independent of the Evidence Gate and never changes the primary Top-6. It was derived on
the frozen demand-binding Development fixture, then copied unchanged to the frozen trigger
Development fixture.

## Source Development result

| metric | fixed@7 upper bound | retrieval-disagreement@7 |
|---|---:|---:|
| Primary + consumed recall | 1.0000 | 1.0000 |
| Trigger rate | 1.0000 | 0.6000 |
| Average consumed chunks | 5.0000 | 2.6000 |
| Queries consuming relevant evidence | 4 | 4 |

This reaches the local objective: it preserves the fixed upper-bound recall while reducing trigger
rate by 40 percentage points and average added context by 48%.

## External frozen Development result

On `retrieval_trigger_development_v1.jsonl`, with no threshold changes:

| metric | result |
|---|---:|
| Primary + consumed recall | 0.2500 |
| Primary + available supplemental@6 recall | 0.3333 |
| Trigger rate | 0.6875 |
| Average consumed chunks | 4.0625 |
| Queries consuming relevant evidence | 1 |
| Trigger precision against frozen intent | 0.5455 |
| Trigger recall against frozen intent | 0.7500 |
| Trigger accuracy against frozen intent | 0.5625 |

The candidate fires frequently but consumes relevant evidence in only one query. It also loses one
available supplemental hit relative to the fixed channel. The vector score-gap and heading-score
thresholds do not transfer reliably across the two Development fixtures.

## Decision

Reject `retrieval-disagreement@7`. Its strong source-fixture result is overfit and does not justify a
regression run. Keep `fixed@7` only as an upper bound and keep the production default unchanged.
Further threshold sweeps on either frozen fixture should stop; a next candidate needs a different,
more structural retrieval signal rather than another score cutoff. Regression, validation,
acceptance, and holdout were not run.

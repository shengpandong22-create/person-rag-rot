# Heading Supplemental Consumption @7

## Fixed protocol

- Dataset: frozen demand-binding Development fixture
- Primary retrieval: vector-only, top_k=6, candidate_k=20
- Supplemental source: heading-shadow
- Supplemental budget: at most 7 chunks
- Demand-binding policy: none; the production Evidence Gate is unchanged
- Primary Top-6 is immutable in both candidates.

## Comparison

| metric | no consumption | fixed@7 | evidence-gated@7 |
|---|---:|---:|---:|
| Primary Recall@6 | 0.6000 | 0.6000 | 0.6000 |
| Primary + actually consumed recall | 0.6000 | 1.0000 | 0.6000 |
| Trigger rate | 0.0000 | 1.0000 | 0.2000 |
| Average consumed supplemental chunks | 0.0000 | 5.0000 | 1.0000 |
| Queries consuming relevant supplemental evidence | 0 | 4 | 0 |
| Negative rejection | 0.6000 | 0.6000 | 0.6000 |
| Evidence accuracy | 0.8667 | 0.8667 | 0.8667 |

`fixed@7` recovers all four positive sources missed by vector candidate@20 while preserving the
primary Top-6. Its cost is unconditional expansion: every query triggers and the context grows from
6 to 11 chunks on average.

`evidence-gated@7` does not recover any of the four sources. The existing production Gate already
accepts those primary results, so it never triggers supplemental consumption for the cases that need
it. Its three triggers occur elsewhere and add no labeled evidence.

## Decision

- Reject `evidence-gated@7` as a retrieval trigger.
- Retain `fixed@7` only as a Development retrieval upper bound, not as a production candidate. It
  proves the heading channel contains the missing evidence but pays an 83% average context increase
  and does not improve the unchanged Gate's rejection behavior.
- The next candidate must use retrieval-side signals independent of the Evidence Gate to approach
  fixed@7 recall with a substantially lower trigger rate/context budget. No RRF tuning is justified.
- Regression, validation, acceptance, and holdout were not run.

# Structural Heading Trigger Evaluation

## Scope

The Gate line is paused. This experiment reads only the question, primary Top-6 heading paths, and
heading-shadow paths. It does not read retrieval scores, Evidence Gate outputs, labels, or case ids,
and it does not consume supplemental chunks or modify retrieval results while producing features.

Offline feature reports were generated for both frozen Development fixtures before the boolean rule
was evaluated. Each row records:

- core query terms covered or missing in primary headings;
- terms newly covered by supplemental headings;
- same-document/different-heading relationships;
- per-clause primary coverage and supplemental gain;
- supplemental concept novelty.

## Predeclared rule

Trigger when all three conditions hold:

1. primary heading coverage is below 0.20;
2. supplemental headings add at least one missing core term;
3. at least one supplemental candidate is from a primary document under a new heading path.

The `0.20` rule and boolean structure were fixed before cross-fixture evaluation and were not changed
after observing the second fixture.

## Results

| fixture | combined recall@primary+supp7 | trigger rate | relevant consumptions | consumption precision |
|---|---:|---:|---:|---:|
| Demand-binding Development | 1.0000 | 0.4667 | 4 | 0.5714 |
| Trigger Development | 0.3333 | 0.6250 | 2 | 0.2000 |

On both fixtures the rule reaches the available `fixed@7` recall upper bound while triggering less
than 100% of queries. However, relevant supplemental consumption precision collapses from 57.14% to
20% on the cross-Development check, far below the required improvement over the previous 54.55%
candidate. Structurally similar hard negatives also satisfy the rule because heading coverage cannot
determine whether the requested value or conclusion exists in the section.

## Decision

Reject the structural boolean rule and do not add it to the eval runner or production assembly. The
experiment shows that heading topology and query-term coverage can preserve the fixed recall upper
bound, but cannot by themselves provide an adequately precise trigger across fixtures.

Do not sweep the 0.20 threshold on these frozen datasets. A next candidate would need a richer
retrieval-only notion of evidence presence, such as value-bearing or relation-bearing heading/chunk
structure, tested on new Development data. Regression, validation, acceptance, and holdout were not
run.

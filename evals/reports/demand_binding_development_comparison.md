# Demand-Binding Frozen Development Comparison

## Fixed protocol

- Dataset: `retrieval_demand_binding_development_v1.jsonl`
- Dataset SHA-256: `c0f501397764d9c42d006d7eec6ba6dbcd36248fd01219f1072b2a0e3dcff3df`
- Retrieval: `vector-only`, `top_k=6`, `candidate_k=20`
- Candidate expansion: `heading-shadow`, consumption=`none`
- Reference: production Evidence Gate with demand binding=`none`
- Candidate: the same Gate followed by demand binding=`numeric-local-v1`
- Regression, validation, acceptance, and holdout datasets were not run.

## Aggregate comparison

| metric | production Gate reference | numeric-local-v1 |
|---|---:|---:|
| Evidence sufficient accuracy | 0.8667 | 1.0000 |
| Full answerability accuracy | 1.0000 | 1.0000 |
| Negative rejection accuracy | 0.6000 | 1.0000 |
| Recall@6 | 0.6000 | 0.6000 |
| Candidate recall@20 | 0.6000 | 0.6000 |

The candidate correctly rejected the two reference false acceptances:

- `db-ex-003`: unsupported `99.9%` Reviewer SLA;
- `db-ta-003`: unsupported `30`-day retention value in the state-impact table.

It introduced no answerability-level positive rejection on this fixture.

## Strict binding audit

The aggregate 100% is not sufficient to qualify the candidate. Four of ten positive rows did not
retrieve their labeled source at candidate@20 (`db-ex-002`, `db-un-002`, `db-ra-002`, and
`db-ta-002`), but both configurations still accepted them. Therefore those rows demonstrate an
answerability decision, not a verified value-to-source binding.

Using the stricter positive condition "labeled evidence retrieved and Gate accepted":

| measure | reference | numeric-local-v1 |
|---|---:|---:|
| Strict supported-positive success | 6/10 | 6/10 |
| Unsupported-negative rejection | 3/5 | 5/5 |

The current parser also treats several requested feature forms as vacuous passes rather than tested
bindings:

- unit aliases `几回` and `几成` are not normalized to numeric/unit demands;
- range questions without literal numbers are not represented as range demands;
- table values are processed as flattened sentences, without retaining cell/row relationships;
- cross-sentence examples may match repeated values in unrelated retrieved sentences instead of a
  connected evidence span.

## Decision

`numeric-local-v1` is **not yet qualified for regression**. It provides a real, narrow improvement
for unsupported explicit values, but the frozen fixture exposes four unverified positive accepts and
four incomplete feature representations. The next Development-only increment should add typed
demand extraction for unit aliases and ranges, plus provenance-aware table rows and bounded
multi-sentence spans. It must be evaluated on this unchanged frozen dataset, while reporting strict
labeled-evidence binding separately from answerability accuracy.

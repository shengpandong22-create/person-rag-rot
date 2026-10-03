# Relation-Value Binding V2 Blind Qualification

## Frozen protocol

- Candidate implementation: `4d611f7`
- Threshold declaration: `44f99a3`
- Fixture freeze: `021a4f7`
- Run commit: `021a4f7fe0fe10b2930f3870f93ba682cac3b894`
- Dataset SHA-256: `3b450912e3786029297e482efdae0548a8b941b7c83bcaa23a198ca601ea4a09`
- Freeze manifest SHA-256: `56f559fff3caf7bdb7620ea07d9dfbff5c306ce0161ae0b4656b19ccde376a1b`
- Retrieval: `vector-only + heading-shadow + supplemental-consumption=none`
- Knowledge base fingerprint: `c7ad10b8c60db236b797763c38a3eb3578827b2f6d2aa6535e0885ebce13ae27`

The candidate was run once after the threshold and fixture commits. It was not modified or rerun.

## Qualification result

**Not qualified. Keep V2 eval-only and do not run regression.**

| gate | required | result | pass |
|---|---:|---:|---:|
| Provenance-aware binding accuracy | >= 0.85 | 0.6250 | no |
| All-positive labeled binding recall | >= 0.80 | 0.5000 | no |
| Candidate-available conditional recall | >= 0.90 | 0.5556 | no |
| Negative rejection | 1.00 | 0.8333 | no |
| Wrong-provenance-only acceptance | 0 | 0 | yes |
| Every span type has a correct positive | yes | table row has 0 | no |

Correct positive bindings by type:

- `sentence_span`: 1/3
- `table_row`: 0/2
- `code_statement`: 2/3
- `bounded_multi_span`: 2/2

## Failure attribution

- Candidate-recall miss: `rvb-t-001`.
- Candidate available but not bound: `rvb-s-001`, `rvb-s-003`, `rvb-t-002`, `rvb-c-002`.
- False acceptance: `rvb-b-004`; the binder confuses an 18% lexical-coverage threshold with a
  claimed 18% retrieval-accuracy guarantee.
- Wrong-provenance-only positive acceptance: none.

The result shows that V2 learned useful patterns from the first Development fixture but does not
generalize across sentence/table structures or relation semantics. The main binding weakness is not
just candidate recall: four of nine positives with available labeled evidence still fail.

## Decision

Do not modify V2 against this blind fixture and do not rerun it. The next candidate must be designed
back on non-blind Development data around typed relation roles, explicit value semantics, and
provenance-local structural parsing. This blind fixture is now spent and remains evidence for the V2
decision only.

Regression, validation, acceptance, and holdout were not run.

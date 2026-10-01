# Demand-Binding Development Fixture

## Purpose

`retrieval_demand_binding_development_v1.jsonl` is an independent Development fixture for the
eval-only deterministic demand-binding layer. It was labeled and frozen before using its failures
to change the candidate. It is not regression, validation, or final acceptance data.

## Composition

The fixture contains 15 human-labeled cases: three cases for each of five binding features. Every
feature has two supported positive demands and one difficult unsupported demand.

| feature | positive | negative | purpose |
|---|---:|---:|---|
| `exact_value` | 2 | 1 | exact constants and unsupported exact promises |
| `unit_alias` | 2 | 1 | Chinese unit/paraphrase forms such as 次/回 and half/0.5 |
| `range_value` | 2 | 1 | closed ranges and unsupported target ranges |
| `table_value` | 2 | 1 | values whose authoritative evidence is in a table or code/table chunk |
| `cross_sentence` | 2 | 1 | values requiring a multi-line or multi-sentence evidence binding |

All ten positive source labels resolve against the current seven-document knowledge base. Question
text has no overlap with the other `retrieval_*.jsonl` datasets.

## Freeze

- Dataset SHA-256: `c0f501397764d9c42d006d7eec6ba6dbcd36248fd01219f1072b2a0e3dcff3df`
- Manifest: `DEMAND_BINDING_DEVELOPMENT_FREEZE.json`
- Any dataset edit invalidates subsequent comparisons and requires a new version and freeze.

## Evaluation order

1. Run the current production Gate without demand binding as the fixed reference.
2. Run `numeric-local-v1` with the same retrieval and evidence configuration.
3. Report per-feature positive retention and negative rejection separately.
4. Do not change production defaults or run regression unless this fixture shows a useful, explained
   improvement without unacceptable positive rejection.

The formal qualification metric is `labeled_evidence_binding_success_rate`: an accepted positive
counts only when the deterministic binding reports a chunk id resolved from its human
`relevant_sources`. Answerability accuracy remains diagnostic and cannot qualify a candidate alone.

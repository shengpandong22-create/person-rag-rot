# Relation-Value Binding Blind Fixture V1

## Construction contract

This fixture was built after the qualification thresholds were committed and before the first V2
candidate run. It is independent from `retrieval_relation_value_development_v1.jsonl`: question
texts and complete human ground-truth heading paths do not overlap.

## Composition

- 16 human-labeled Development cases;
- 10 positive bindings and 6 hard negatives;
- four cases each for `sentence_span`, `table_row`, `code_statement`, and
  `bounded_multi_span`;
- false-premise, missing-value, wrong-relation, unit, range, code-bound, and provenance pressure;
- all 10 positive label paths resolve against knowledge base
  `b2d70e40-02d1-4a78-af5a-22df85a82693` before the blind run.

The fixture is not regression, validation, acceptance, or holdout data.

## Freeze

- Dataset: `evals/datasets/retrieval_relation_value_blind_v1.jsonl`
- Manifest: `evals/datasets/RELATION_VALUE_BLIND_FREEZE.json`
- SHA-256: `3b450912e3786029297e482efdae0548a8b941b7c83bcaa23a198ca601ea4a09`

After this freeze is committed, V2 may be run once. Per-case output must not be used to tune and
rerun the candidate on this fixture.

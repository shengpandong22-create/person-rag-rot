# Relation-Value Binding Development Fixture

## Purpose

This independent frozen fixture separates true relation-to-value support from chunks that merely
contain related headings, incidental numbers, formulas, or examples. It was created and frozen
before implementing a new relation-value binding candidate.

## Contract

Every row contains human labels for:

- `requested_relation`: the relation whose value is requested;
- `expected_values`: exact supported values for positives, empty for negatives;
- `canonical_unit`: normalized unit when applicable;
- `evidence_span_type`: the structural evidence boundary;
- `expected_binding`: whether the requested relation is supported;
- stable `document_logical_name + heading_path` sources for positives.

## Composition

There are 12 cases, with two positive bindings and one hard negative for each span type:

- `sentence_span`
- `table_row`
- `code_statement`
- `bounded_multi_span`

All eight positive source paths resolve against the current knowledge base. Questions do not overlap
with any other retrieval dataset.

## Freeze

- Dataset SHA-256: `9156164ba289b2407b104c85a717d58149e8862ef5e2ffba6d4aedad9b20173f`
- Manifest: `RELATION_VALUE_DEVELOPMENT_FREEZE.json`

Editing the dataset invalidates all later comparisons. This fixture is Development data, not
regression, validation, acceptance, or holdout data.

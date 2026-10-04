# Relation-Value Binding V3 Freeze Qualification

## Purpose

This protocol is declared before V3 is frozen. It decides only whether the current eval-only V3
implementation is stable enough to become a fixed candidate for later safety validation. Passing
does not authorize regression, validation, acceptance, holdout, production wiring, or another run
of the spent blind fixture.

## Candidate identity

- Candidate name: `relation-value-binding-v3`
- Candidate implementation commit: `d55d2c7`
- Original Development dataset:
  `evals/datasets/retrieval_relation_value_development_v1.jsonl`
- Semantic-role Development dataset:
  `evals/datasets/relation_value_role_development_v1.jsonl`

## Hard qualification gates

The candidate must satisfy every gate in one reproducible evaluation snapshot.

### Original relation-value Development

- provenance-aware binding accuracy >= 0.90;
- human-labeled binding recall >= 0.875;
- negative rejection = 1.00;
- every declared span type has at least one correct positive binding.

The known `rv-t-002` candidate-recall miss remains in the denominator and cannot be waived.

### Semantic-role confusion Development

- paired-case accuracy = 1.00;
- positive value recall = 1.00;
- negative rejection = 1.00;
- all six pair ids are present and both sides of every pair are correct.

### Diagnostic binding volume

- original Development average bindings per case <= 3.0;
- original Development maximum bindings in one case <= 15;
- maximum bindings from one chunk in one case <= 3;
- role-confusion Development average bindings per case <= 1.5;
- role-confusion Development maximum bindings per case <= 3.

## Integrity and decision rules

- Both input reports and their SHA-256 hashes must be recorded.
- The qualification output must record the evaluated Git commit and threshold file hash.
- Any failed hard gate keeps V3 unfrozen and eval-only.
- Passing permits a separate commit that freezes the V3 implementation and its Development
  evidence; it does not permit changing production defaults.
- After a candidate freeze, implementation changes require a new candidate version.
- The spent independent blind fixture must not be read for tuning or rerun.

# Relation-Value Binding V3 Candidate Freeze

V3 is frozen as an **eval-only candidate** after passing the predeclared Development qualification
gates. The freeze does not change production behavior and does not authorize any formal split run.

## Identity

- Candidate: `relation-value-binding-v3`
- Implementation commit: `d55d2c7`
- Freeze manifest: `evals/datasets/RELATION_VALUE_V3_CANDIDATE_FREEZE.json`
- Manifest SHA-256: `4c274e604bdd369e01d276398b15cd625fa18ac35d1265054d1fd99665a75e81`

## Frozen surface

The manifest records SHA-256 hashes for:

1. the V3 implementation;
2. the original relation-value Development dataset;
3. the semantic-role confusion Development dataset;
4. the original Development result report;
5. the semantic-role result report;
6. the predeclared freeze qualification thresholds.

Any hash change invalidates this candidate identity. Further implementation changes require a new
candidate version and a new qualification/freeze cycle.

## Boundary

No retrieval, binder evaluation, regression, validation, acceptance, holdout, or spent blind fixture
was run while creating this freeze. Production defaults remain unchanged.

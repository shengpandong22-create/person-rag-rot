# Relation-Value Binding V3 Freeze Qualification Result

## Outcome

**Qualified for an eval-only candidate freeze.**

This result permits a later, separate freeze commit. It does not authorize regression, validation,
acceptance, holdout, production integration, or another run of the spent blind fixture.

## Predeclared gate results

| group | gate | required | observed | pass |
|---|---|---:|---:|---:|
| Original Development | Provenance-aware accuracy | >= 0.90 | 0.9167 | yes |
| Original Development | Labeled binding recall | >= 0.875 | 0.8750 | yes |
| Original Development | Negative rejection | 1.00 | 1.0000 | yes |
| Original Development | Every span type success | >= 1 | minimum 1 | yes |
| Binding volume | Average bindings/case | <= 3.0 | 2.6667 | yes |
| Binding volume | Maximum bindings/case | <= 15 | 13 | yes |
| Binding volume | Maximum bindings/chunk | <= 3 | 3 | yes |
| Semantic-role Development | Paired accuracy | 1.00 | 1.0000 | yes |
| Semantic-role Development | Positive value recall | 1.00 | 1.0000 | yes |
| Semantic-role Development | Negative rejection | 1.00 | 1.0000 | yes |
| Semantic-role Development | Complete correct pairs | 6 | 6 | yes |
| Semantic-role volume | Average bindings/case | <= 1.5 | 1.0000 | yes |
| Semantic-role volume | Maximum bindings/case | <= 3 | 3 | yes |

## Reproducibility

- Candidate implementation commit: `d55d2c7`
- Threshold declaration commit: `4674598`
- Threshold SHA-256: `5297d8108abb9596417765d43302a7ec1fd5435830bde47c78c35dcbd6f3dcab`
- Original report SHA-256: `5ea556b68d58a023e69dc89edbb3284765e91dd118018bcef21a55ad8e063892`
- Semantic-role report SHA-256: `277af007e704d7668707cbeef3fe7e96e655703e607a8bc270c877c233017f51`

## Decision

V3 may now be frozen as a named eval-only candidate in a separate commit. The freeze should hash
the implementation, both Development datasets, both result reports, and the threshold definition.
No formal split should run as part of that freeze operation.

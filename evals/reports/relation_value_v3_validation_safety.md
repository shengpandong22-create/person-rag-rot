# Relation-Value V3 Validation Safety Result

## Decision

`relation-value-binding-v3` passed the single validation safety run authorized by commit
`65a72825161cc6812e7cf552b1f227ad32092e28`. All predeclared hard checks passed and the
machine-readable decision is `safe_for_next_protocol=true`.

This establishes only that the frozen V3 candidate and its eval tooling did not change the current
retrieval and Evidence Gate behavior on regression or validation. It does not establish V3 binding
quality and does not authorize production integration.

## Results

| Gate | Required | Observed | Result |
| --- | ---: | ---: | --- |
| Recall@1 | >= 0.3529 | 0.3529 | pass |
| Recall@3 | >= 0.5294 | 0.5294 | pass |
| Recall@6 | >= 0.7059 | 0.7059 | pass |
| MRR | >= 0.4853 | 0.4853 | pass |
| Full answerability accuracy | = 1.0 | 1.0 | pass |
| Partial answerability accuracy | = 1.0 | 1.0 | pass |
| Negative rejection accuracy | = 1.0 | 1.0 | pass |
| Candidate recall@20 | >= 0.8824 | 0.8824 | pass |
| Average returned candidates | = 6.0 | 6.0 | pass |
| Retrieval P95 | <= 1000 ms | 32.6679 ms | pass |

All 22 rows were graded and all 17 human relevant-source labels were resolved. The dataset hash,
validation freeze hash, fixed configuration, V3 candidate freeze, and production isolation checks
all passed. Retrieval P50 was 24.5834 ms.

## Audit artifacts

- Raw report: `evals/reports/relation_value_v3_validation_safety/retrieval_eval.json`.
- Rendered per-case report:
  `evals/reports/relation_value_v3_validation_safety/retrieval_eval.md`.
- Machine-readable decision:
  `evals/reports/relation_value_v3_validation_safety/qualification.json`.
- Raw report SHA-256:
  `a6adf69976844bdd2d2d2f5c43840db5ccf282b1d2ca5aee606af2b26bb35da8`.

## Scope limitation

The run intentionally used `demand_binding_policy=none`. Validation has no human relation-role,
target-value, canonical-unit, provenance-binding, or structural-span labels. Enabling V3 or deriving
labels from the validation questions would not produce an auditable quality score. The report's
binding-specific diagnostic fields therefore are not V3 effectiveness metrics.

## Result branch

The candidate is eligible only for preparation of a new independent acceptance dataset. That set
must include human labels for relation role, target value, unit, provenance, structural span, and
hard negatives. The dataset, freeze manifest, acceptance thresholds, and single-run protocol must
be reviewed and committed before V3 is run on it.

No holdout, prior blind fixture, or acceptance dataset was run. Production integration remains
unauthorized and would require a separate feature-flag, default-off, rollback, monitoring, and
integration-test design after independent acceptance passes.

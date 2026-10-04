# Relation-Value V3 Regression Safety Result

## Decision

`relation-value-binding-v3` passed the predeclared regression safety protocol. This result only
permits preparation of a separate validation protocol. It does not authorize validation,
acceptance, holdout, blind-fixture reuse, or production integration.

## Audit trail

- Protocol commit: `9e04a54cfece6b6d7fe4ec82c1394debd21fa547`.
- Candidate freeze manifest remained intact before and after the run.
- The first host attempt failed before producing a report because the Windows PyTorch runtime could
  not load `torch_global_deps.dll`. The permitted infrastructure retry used the repository's API
  image, current source tree, existing database network, and the exact committed configuration.
- Completed report: `evals/reports/relation_value_v3_regression_safety/retrieval_eval.json`.
- Machine-readable decision:
  `evals/reports/relation_value_v3_regression_safety/qualification.json`.

## Results

| Gate | Required | Observed | Result |
| --- | ---: | ---: | --- |
| Recall@1 | >= 0.20 | 0.20 | pass |
| Recall@3 | >= 0.40 | 0.40 | pass |
| Recall@6 | >= 0.45 | 0.45 | pass |
| MRR | >= 0.3017 | 0.3017 | pass |
| Full answerability accuracy | >= 0.8824 | 0.8824 | pass |
| Negative rejection accuracy | >= 0.50 | 0.50 | pass |
| Candidate recall@20 | >= 0.60 | 0.80 | pass |
| Average returned candidates | = 6.0 | 6.0 | pass |
| Retrieval P95 | <= 1000 ms | 35.7446 ms | pass |

All 30 rows were graded. All 20 human relevant-source labels were resolved. The exact fixed
retrieval and Gate configuration matched the protocol, and no production source imports the V3
eval-only implementation.

## Scope limitation

Regression has no human relation, canonical-unit, or structural-span labels. Consequently, this
run validates production-path safety only; it does not claim a new V3 binding-quality score and did
not generate proxy labels from question text. V3 binding quality remains represented by the frozen
Development artifacts.

## Next permitted step

Declare and commit a validation protocol and its pass thresholds. Do not run validation until that
protocol exists, and do not run any holdout or independent blind acceptance set under this result.

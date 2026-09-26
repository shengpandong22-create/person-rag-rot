# Clause- and Demand-Aware Candidate Cross-Split Validation

Fixed candidate: `clause_demand_v1`.

The policy was defined and selected on development, then replayed unchanged on
regression and frozen validation. It has no numeric threshold. Retrieval
remained vector-only, production behavior was unchanged, and holdout was not
run.

## Results

| Split | Policy | Full accept | Partial boundary | None reject | Macro accuracy |
|---|---|---:|---:|---:|---:|
| development | current binary | 0.9333 | 0.0000 | 0.2000 | 0.3778 |
| development | clause_demand_v1 | 0.9333 | 0.9000 | 0.4571 | 0.6778 |
| regression | current binary | 0.8824 | 0.0000 | 0.5000 | 0.4608 |
| regression | clause_demand_v1 | 0.8824 | 0.0000 | 0.5000 | 0.4608 |
| validation | current binary | 1.0000 | 0.0000 | 1.0000 | 0.6667 |
| validation | clause_demand_v1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

## Regression safety result

The candidate produces exactly the same regression decisions as the current
binary Gate. It introduces no full-case loss and no negative-reason regression.
The two rejected full cases, `ret-007` and `ret-020`, are existing baseline
failures rather than candidate regressions. Recall@6 remains 0.45 and MRR
remains 0.3017.

The generic replay command reports no "eligible candidate" because its
development-ranking filter requires an absolute full acceptance of at least
0.90 and a strict increase in none rejection. That generic filter is not the
cross-split safety decision: the predefined regression rule compares the fixed
candidate with the regression baseline and permits at most one new full loss.
This candidate has zero.

## Validation result

All 15 full cases remain full, both partial cases are identified as partial,
and all five none cases remain rejected. Recall@6 remains 0.7059 and MRR
remains 0.4853. There are no false-full or false-rejection cases.

## Decision

`clause_demand_v1` passes regression safety and frozen-validation verification
as an eval-only candidate. The result supports a separate review of whether to
implement the policy behind an explicit production configuration. It does not
authorize a production-default change or a holdout run.

Detailed reports:

- `regression_clause_demand/vector-only/retrieval_eval.json`
- `regression_clause_demand/calibration/gate_calibration.json`
- `validation_clause_demand/vector-only/retrieval_eval.json`
- `validation_clause_demand/calibration/gate_calibration.json`

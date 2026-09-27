# Clause/Demand Gate Enabled-Path Verification

This verifies the real `AnswerService` path with the explicitly configured
`clause_demand_v1` policy. It is not an offline replay. The application default
remains `current_binary_v1`; no production environment was switched.

## Results

| Split | Full accept | Partial boundary | None reject | Recall@6 | MRR |
|---|---:|---:|---:|---:|---:|
| regression | 0.8824 | 0.0000 | 0.5000 | 0.4500 | 0.3017 |
| validation | 1.0000 | 1.0000 | 1.0000 | 0.7059 | 0.4853 |

The enabled regression path exactly matches its earlier offline replay and the
current binary baseline. It adds no full rejection and introduces no grouped
negative regression. Existing full rejections `ret-007` and `ret-020` remain.

The enabled validation path classifies all 15 full, two partial, and five none
cases correctly. `partial_answerability_accuracy` in the legacy binary metrics
is 0 because it means "partial accepted as sufficient"; the explicit
`partial_boundary_detection_rate` is the applicable metric and is 1.0.

## Configuration contract

- Default: `AGENT_MENTOR_EVIDENCE_GATE_POLICY=current_binary_v1`.
- Candidate opt-in: `AGENT_MENTOR_EVIDENCE_GATE_POLICY=clause_demand_v1`.
- The eval runner also accepts
  `--evidence-gate-policy clause_demand_v1`.
- Unknown policy values fail settings/CLI validation.

## Decision

The implementation is ready for final acceptance evaluation, but the default
must not be switched before that result is reviewed. Holdout was not run in
this step.

Detailed enabled-path reports:

- `regression_clause_demand_enabled/retrieval_eval.json`
- `validation_clause_demand_enabled/retrieval_eval.json`

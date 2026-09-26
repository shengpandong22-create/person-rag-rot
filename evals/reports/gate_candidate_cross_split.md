# Evidence Gate Candidate Cross-Split Validation

Fixed candidate: `specific_coverage_ratio >= 0.30`.

The threshold was selected on development and then replayed unchanged on
regression and frozen validation. Retrieval remained vector-only. No threshold
search, candidate reselection, production behavior change, or holdout run was
performed in this step.

## Cross-split results

| Split | Policy | Full accept | Partial boundary | None reject | Macro accuracy |
|---|---|---:|---:|---:|---:|
| development | current binary | 0.9333 | 0.0000 | 0.2000 | 0.3778 |
| development | coverage >= 0.30 | 0.9333 | 0.7000 | 0.6286 | 0.6111 |
| regression | current binary | 0.8824 | 0.0000 | 0.5000 | 0.4608 |
| regression | coverage >= 0.30 | 0.6471 | 0.3333 | 0.7000 | 0.4935 |
| validation | current binary | 1.0000 | 0.0000 | 1.0000 | 0.6667 |
| validation | coverage >= 0.30 | 0.9333 | 0.5000 | 1.0000 | 0.8111 |

Retrieval Recall/MRR did not change because policy replay uses the saved
retrieval result. Regression remained Recall@6 0.45 / MRR 0.3017, and
validation remained Recall@6 0.7059 / MRR 0.4853.

## Safety assessment

The candidate fails the predefined full-acceptance safety floor on regression:
0.6471 is materially below 0.90. The current binary Gate already rejects
`ret-007` and `ret-020`; the coverage policy additionally moves `ret-008`,
`ret-016`, `ret-023`, and `ret-024` from full to partial.

On validation, the candidate preserves all negative rejections and detects one
of two partial boundaries, but newly moves full case `va-pos-012` to partial.
This result is not enough to override the regression failure.

## Decision

Reject `specific_coverage_ratio >= 0.30` as a production candidate. It is a
useful diagnostic signal but is not stable across independently labelled
splits. The absolute ratio is sensitive to question length and tokenization:
valid full questions with several unmatched wording terms can fall below the
same boundary that separates development hard negatives.

Do not tune another threshold directly against validation. The next
development experiment should replace the global union coverage ratio with
clause- and demand-aware diagnostics, then repeat the same fixed-candidate
regression/validation sequence. Holdout remains untouched.

Detailed reports:

- `regression_gate_candidate/vector-only/retrieval_eval.json`
- `regression_gate_candidate/calibration/gate_calibration.json`
- `validation_gate_candidate/vector-only/retrieval_eval.json`
- `validation_gate_candidate/calibration/gate_calibration.json`

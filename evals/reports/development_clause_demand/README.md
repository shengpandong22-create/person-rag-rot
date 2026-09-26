# Development Clause- and Demand-Aware Gate Candidate

This experiment adds evaluation-only diagnostics for clause coverage and five
explicit demand types: exact values, dates, guarantees, future versions, and
comparisons. Production Evidence Gate behavior, retrieval, and configuration
remain unchanged.

The fixed candidate `clause_demand_v1` maps a currently accepted result to
`partial` when at least one question clause lacks lexical support or an
explicit demand lacks a matching evidence signal. It introduces no tunable
numeric threshold.

## Development result

| Metric | Current binary Gate | clause_demand_v1 |
|---|---:|---:|
| Full acceptance | 0.9333 | 0.9333 |
| Partial boundary detection | 0.0000 | 0.9000 |
| None rejection | 0.2000 | 0.4571 |
| Macro accuracy | 0.3778 | 0.6778 |

The only full case not accepted is `dev-pos-010`, which the current Gate also
rejects. The candidate therefore introduces no additional full-case loss on
development.

## Rejection by negative reason

| Reason | Current | Candidate |
|---|---:|---:|
| false_premise | 0.1250 | 0.3750 |
| in_domain_no_conclusion | 0.2000 | 0.4000 |
| in_domain_value_missing | 0.1429 | 0.2857 |
| out_of_range_implementation | 0.4000 | 0.6000 |
| out_of_scope | 0.2000 | 0.4000 |
| version_not_released | 0.2000 | 0.8000 |

All negative-reason groups improve or remain above the current baseline. The
largest gain is on unreleased-version questions, where explicit future-version
demand is observable even when retrieval returns topically related material.

## Decision

`clause_demand_v1` is the next fixed eval-only candidate. It is not approved
for production. The next step is regression safety validation; validation is
run only after reviewing that result. Holdout remains untouched.

Detailed per-case clause and demand diagnostics are in
`vector-only/retrieval_eval.json`. The complete offline policy comparison is in
`calibration/gate_calibration.json`.

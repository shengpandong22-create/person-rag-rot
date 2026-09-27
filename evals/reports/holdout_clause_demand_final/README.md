# Final Holdout Acceptance: vector-only + clause_demand_v1

This is the single final holdout run for the fixed `clause_demand_v1`
candidate. The frozen holdout was verified before execution:

- cases: 19
- dataset SHA-256:
  `9f9d1dbb04df5147bc7b7f61998f74302d5e45ec8138e4fd7452bd48fadb37c9`
- git commit: `ec7dd5da279acd6ecb89b1b545d6316b83f2d3b8`
- git dirty: false
- retrieval mode: vector-only
- Evidence Gate policy: clause_demand_v1

No parameter or rule will be changed from holdout case outcomes.

## Result

| Metric | Previous current-binary holdout | clause_demand_v1 |
|---|---:|---:|
| Recall@1 | 0.3333 | 0.3333 |
| Recall@3 | 0.5556 | 0.5556 |
| Recall@6 | 0.5556 | 0.5556 |
| MRR | 0.4259 | 0.4259 |
| Full acceptance | 0.8889 | 0.8889 |
| None rejection | 0.3000 | 0.4000 |
| P50 latency | 50.0478 ms | 41.1408 ms |
| P95 latency | 34128.8320 ms | 26793.5944 ms |

The candidate preserves retrieval and full acceptance while converting one
additional negative from false acceptance to correct rejection. It still
accepts six of ten negatives, so the absolute rejection quality remains too
weak for a safe default switch.

## Rejection by negative reason

| Reason | Current binary | clause_demand_v1 |
|---|---:|---:|
| false_premise | 0.3333 | 0.3333 |
| in_domain_no_conclusion | 0.0000 | 1.0000 |
| in_domain_value_missing | 0.2500 | 0.2500 |
| out_of_range_implementation | 0.0000 | 0.0000 |
| version_not_released | 1.0000 | 1.0000 |

Several groups contain very few cases, so a rate of 1.0 must not be treated as
broad proof. The P95 latency is dominated by a first-request/cold-path outlier
in both runs and is not evidence of a policy speedup.

## Failure summary

- false acceptance: 6
- correct rejection: 4
- Evidence Gate rejection of a full case: 1
- candidate recall miss: 1
- per-document filter miss: 2
- adjacent filter miss: 1

## Acceptance decision

The candidate does **not** pass the final quality bar for becoming the default
Evidence Gate. Keep `AGENT_MENTOR_EVIDENCE_GATE_POLICY=current_binary_v1`.
The opt-in implementation may remain available for controlled experiments, but
the holdout result must not be used to tune another rule or threshold. A future
candidate requires a new independently constructed acceptance set before final
evaluation.

The complete per-case report is `retrieval_eval.json` in this directory.

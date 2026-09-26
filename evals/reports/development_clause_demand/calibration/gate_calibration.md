# Evidence Gate Offline Calibration

- source report: `evals\reports\development_clause_demand\vector-only\retrieval_eval.json`
- source SHA-256: `917c601512db3a9107e2f40c7a876f2142d7d1edb50d855de580ce55ee493f5b`
- retrieval rerun: no

| policy | parameters | full accept | partial boundary | none reject | macro accuracy |
|---|---|---:|---:|---:|---:|
| current_binary_v1 | `{}` | 0.9333 | 0.0 | 0.2 | 0.3778 |
| specific_coverage_ratio | `{"minimum": 0.15}` | 0.9333 | 0.2 | 0.2286 | 0.4444 |
| specific_coverage_ratio | `{"minimum": 0.2}` | 0.9333 | 0.3 | 0.3429 | 0.4778 |
| specific_coverage_ratio | `{"minimum": 0.25}` | 0.9333 | 0.5 | 0.5143 | 0.5444 |
| specific_coverage_ratio | `{"minimum": 0.3}` | 0.9333 | 0.7 | 0.6286 | 0.6111 |
| specific_coverage_ratio | `{"minimum": 0.35}` | 0.8667 | 0.9 | 0.7714 | 0.6556 |
| specific_coverage_ratio | `{"minimum": 0.4}` | 0.8667 | 0.9 | 0.8571 | 0.6556 |
| specific_coverage_ratio | `{"minimum": 0.45}` | 0.7333 | 1.0 | 0.9429 | 0.6444 |
| specific_coverage_ratio | `{"minimum": 0.5}` | 0.6 | 1.0 | 0.9429 | 0.6 |
| specific_covered_terms | `{"minimum": 2}` | 0.9333 | 0.0 | 0.2 | 0.3778 |
| specific_covered_terms | `{"minimum": 3}` | 0.9333 | 0.2 | 0.4 | 0.4444 |
| specific_covered_terms | `{"minimum": 4}` | 0.8 | 0.2 | 0.5143 | 0.4 |
| specific_covered_terms | `{"minimum": 5}` | 0.7333 | 0.2 | 0.6286 | 0.3778 |
| specific_covered_terms | `{"minimum": 6}` | 0.6667 | 0.3 | 0.7714 | 0.3889 |
| specific_covered_terms | `{"minimum": 7}` | 0.3333 | 0.7 | 0.8286 | 0.4111 |
| specific_covered_terms | `{"minimum": 8}` | 0.3333 | 0.8 | 0.8571 | 0.4444 |
| numeric_demand_coverage | `{}` | 0.9333 | 0.0 | 0.2571 | 0.3778 |
| clause_demand_v1 | `{}` | 0.9333 | 0.9 | 0.4571 | 0.6778 |

## Eligible candidates

- `clause_demand_v1` {}: macro=0.6778, full=0.9333, partial=0.9, none=0.4571; full losses=['dev-pos-010']
- `specific_coverage_ratio` {'minimum': 0.3}: macro=0.6111, full=0.9333, partial=0.7, none=0.6286; full losses=['dev-pos-010']
- `specific_coverage_ratio` {'minimum': 0.25}: macro=0.5444, full=0.9333, partial=0.5, none=0.5143; full losses=['dev-pos-010']
- `specific_coverage_ratio` {'minimum': 0.2}: macro=0.4778, full=0.9333, partial=0.3, none=0.3429; full losses=['dev-pos-010']
- `specific_covered_terms` {'minimum': 3}: macro=0.4444, full=0.9333, partial=0.2, none=0.4; full losses=['dev-pos-010']
- `specific_coverage_ratio` {'minimum': 0.15}: macro=0.4444, full=0.9333, partial=0.2, none=0.2286; full losses=['dev-pos-010']
- `numeric_demand_coverage` {}: macro=0.3778, full=0.9333, partial=0.0, none=0.2571; full losses=['dev-pos-010']

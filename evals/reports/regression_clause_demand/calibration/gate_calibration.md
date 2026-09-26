# Evidence Gate Offline Calibration

- source report: `evals\reports\regression_clause_demand\vector-only\retrieval_eval.json`
- source SHA-256: `eae603fa90a875e89770ca56c069c913bf1d7cf2b29e037ee89d6808c8d96ab5`
- retrieval rerun: no

| policy | parameters | full accept | partial boundary | none reject | macro accuracy |
|---|---|---:|---:|---:|---:|
| current_binary_v1 | `{}` | 0.8824 | 0.0 | 0.5 | 0.4608 |
| specific_coverage_ratio | `{"minimum": 0.15}` | 0.8235 | 0.0 | 0.5 | 0.4412 |
| specific_coverage_ratio | `{"minimum": 0.2}` | 0.8235 | 0.0 | 0.7 | 0.4412 |
| specific_coverage_ratio | `{"minimum": 0.25}` | 0.7059 | 0.3333 | 0.7 | 0.5131 |
| specific_coverage_ratio | `{"minimum": 0.3}` | 0.6471 | 0.3333 | 0.7 | 0.4935 |
| specific_coverage_ratio | `{"minimum": 0.35}` | 0.5882 | 0.3333 | 0.7 | 0.4738 |
| specific_coverage_ratio | `{"minimum": 0.4}` | 0.4706 | 0.3333 | 0.7 | 0.4346 |
| specific_coverage_ratio | `{"minimum": 0.45}` | 0.3529 | 0.3333 | 0.8 | 0.3954 |
| specific_coverage_ratio | `{"minimum": 0.5}` | 0.3529 | 0.3333 | 0.8 | 0.3954 |
| specific_covered_terms | `{"minimum": 2}` | 0.8824 | 0.0 | 0.7 | 0.4608 |
| specific_covered_terms | `{"minimum": 3}` | 0.7647 | 0.0 | 0.7 | 0.4216 |
| specific_covered_terms | `{"minimum": 4}` | 0.7059 | 0.3333 | 0.7 | 0.5131 |
| specific_covered_terms | `{"minimum": 5}` | 0.4706 | 0.3333 | 0.8 | 0.4346 |
| specific_covered_terms | `{"minimum": 6}` | 0.2941 | 0.3333 | 0.9 | 0.3758 |
| specific_covered_terms | `{"minimum": 7}` | 0.2353 | 0.3333 | 1.0 | 0.3562 |
| specific_covered_terms | `{"minimum": 8}` | 0.1176 | 0.3333 | 1.0 | 0.317 |
| numeric_demand_coverage | `{}` | 0.8824 | 0.0 | 0.6 | 0.4608 |
| clause_demand_v1 | `{}` | 0.8824 | 0.0 | 0.5 | 0.4608 |

## Eligible candidates

No candidate passed the safety constraints.
